import logging

from base_agent import BaseAgent
from boundary import LLMBoundary
from models import SubTask, AgentResult, GenericAuditAgentConfig

logger = logging.getLogger(__name__)


class GenericAuditAgent(BaseAgent):
    name = "generic_audit"
    _system_prompt = (
        "You are a broad security auditor. "
        "Given a description of code, an endpoint, or a system, perform a general security review. "
        "Cover any security concerns not addressed by specialised auditors: "
        "data exposure, insecure defaults, configuration issues, and anything suspicious. "
        "Report: issue type, affected component, severity (high/medium/low), brief explanation. "
        "If no issues found, say so explicitly."
    )
    _tools = []

    def __init__(self, config: GenericAuditAgentConfig, llm_provider) -> None:
        self._config = config
        self._llm = llm_provider

    def execute(self, subtask: SubTask) -> AgentResult:
        try:
            if not subtask.task_type or not subtask.context:
                return AgentResult(
                    task_type=subtask.task_type,
                    success=False,
                    failure_mode="precondition_violated",
                )

            boundary = LLMBoundary()

            check = boundary.check_input(subtask.context)
            if not check.safe:
                return AgentResult(
                    task_type=subtask.task_type,
                    success=False,
                    failure_mode=check.failure_mode,
                )

            response = self._call_llm(subtask.context)
            if response is None:
                return AgentResult(
                    task_type=subtask.task_type,
                    success=False,
                    failure_mode="agent_llm_unavailable",
                )

            check = boundary.check_output(response)
            if not check.safe:
                return AgentResult(
                    task_type=subtask.task_type,
                    success=False,
                    failure_mode=check.failure_mode,
                )

            return AgentResult(task_type=subtask.task_type, success=True, content=response)

        except Exception:
            logger.exception("Unhandled error in GenericAuditAgent.execute")
            return AgentResult(
                task_type=subtask.task_type,
                success=False,
                failure_mode="agent_execution_error",
            )
