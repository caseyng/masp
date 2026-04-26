import sys
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

from auditor import Auditor
from decomposer import Decomposer
from models import (
    Config,
    SubTask,
    AgentResult,
    AuditReport,
    PipelineError,
    DecomposerError,
    RegistryKeyError,
    AuditWriteError,
)
from registry import Registry

_BOUNDARY_FAILURE_MODES = {"boundary_injection_detected", "boundary_output_unsafe"}


class Orchestrator:
    def __init__(
        self,
        config: Config,
        registry: Registry,
        decomposer: Decomposer,
        auditor: Auditor,
        llm_provider,
    ) -> None:
        self._config = config
        self._registry = registry
        self._decomposer = decomposer
        self._auditor = auditor
        self._llm = llm_provider
        self._closed = False

    def run(self, audit_request: str) -> AuditReport:
        if self._closed:
            raise RuntimeError("Orchestrator has been closed")

        run_id = str(uuid.uuid4())[:8]

        # Log run_started before validation so audit trail records the attempt.
        self._safe_log("run_started", {
            "run_id": run_id,
            "audit_request_length": len(audit_request) if audit_request else 0,
        })

        if not audit_request or not isinstance(audit_request, str):
            raise ValueError("audit_request must be a non-empty string")

        # Decompose
        try:
            subtasks = self._decomposer.decompose(audit_request)
        except DecomposerError as e:
            if e.failure_mode in _BOUNDARY_FAILURE_MODES:
                self._safe_log("boundary_violation", {
                    "run_id": run_id,
                    "failure_mode": e.failure_mode,
                    "call_site": "decomposer",
                })
                # Emit agent_complete so test harness can detect boundary failure mode.
                self._safe_log("agent_complete", {
                    "run_id": run_id,
                    "task_type": "decomposer",
                    "success": False,
                    "failure_mode": e.failure_mode,
                })
            self._safe_log("pipeline_error", {
                "run_id": run_id,
                "failure_mode": "decomposer_failed",
                "reason": e.failure_mode,
            })
            raise PipelineError("decomposer_failed", reason=e.failure_mode) from e

        # Deduplicate by task_type — first occurrence wins (§2b)
        seen: set[str] = set()
        unique_subtasks: list[SubTask] = []
        for t in subtasks:
            if t.task_type not in seen:
                seen.add(t.task_type)
                unique_subtasks.append(t)

        self._safe_log("decompose_complete", {
            "run_id": run_id,
            "subtask_count": len(unique_subtasks),
        })

        # Registry lookup — unknown types become failed AgentResults immediately
        results: list[AgentResult] = []
        agents_to_run: list[tuple[SubTask, type, object]] = []
        for subtask in unique_subtasks:
            try:
                agent_class = self._registry.get(subtask.task_type)
                agent_config = self._config.agent_configs[subtask.task_type]
                agents_to_run.append((subtask, agent_class, agent_config))
            except RegistryKeyError:
                results.append(AgentResult(
                    task_type=subtask.task_type,
                    success=False,
                    failure_mode="unknown_task_type",
                ))

        if not agents_to_run and not results:
            self._safe_log("pipeline_error", {
                "run_id": run_id,
                "failure_mode": "no_agents_spawned",
            })
            raise PipelineError("no_agents_spawned")

        if not agents_to_run and results:
            self._safe_log("pipeline_error", {
                "run_id": run_id,
                "failure_mode": "no_agents_spawned",
            })
            raise PipelineError("no_agents_spawned")

        # Log agent_started before submitting to thread pool
        for subtask, _, _ in agents_to_run:
            self._safe_log("agent_started", {
                "run_id": run_id,
                "task_type": subtask.task_type,
            })

        # Concurrent execution — all agents run simultaneously, all futures collected
        with ThreadPoolExecutor(max_workers=self._config.max_workers) as pool:
            futures = {
                pool.submit(agent_class(subtask, agent_config, self._llm).execute, subtask): subtask.task_type
                for subtask, agent_class, agent_config in agents_to_run
            }

            for future in as_completed(futures):
                task_type = futures[future]
                try:
                    result = future.result()
                except Exception:
                    result = AgentResult(
                        task_type=task_type,
                        success=False,
                        failure_mode="agent_execution_error",
                    )

                if result.failure_mode in _BOUNDARY_FAILURE_MODES:
                    self._safe_log("boundary_violation", {
                        "run_id": run_id,
                        "failure_mode": result.failure_mode,
                        "call_site": "agent",
                        "task_type": task_type,
                    })

                results.append(result)
                event_data: dict = {
                    "run_id": run_id,
                    "task_type": task_type,
                    "success": result.success,
                }
                if not result.success:
                    event_data["failure_mode"] = result.failure_mode
                self._safe_log("agent_complete", event_data)

        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        sufficient = successful >= self._config.sufficiency_threshold

        report = AuditReport(
            run_id=run_id,
            audit_request=audit_request,
            results=results,
            sufficient=sufficient,
            successful_count=successful,
            failed_count=failed,
            sufficiency_threshold=self._config.sufficiency_threshold,
        )

        self._safe_log("run_complete", {
            "run_id": run_id,
            "successful_count": successful,
            "failed_count": failed,
            "sufficient": sufficient,
        })

        return report

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._auditor.close()

    def _safe_log(self, event: str, data: dict) -> None:
        try:
            self._auditor.log(event, data)
        except Exception as e:
            print(f"audit_write_failed: {e}", file=sys.stderr)

    def __repr__(self) -> str:
        return f"Orchestrator(closed={self._closed})"
