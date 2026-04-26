from __future__ import annotations
from dataclasses import dataclass, field


class PipelineError(Exception):
    def __init__(self, failure_mode: str, reason: str | None = None):
        self.failure_mode = failure_mode
        self.reason = reason
        super().__init__(failure_mode)


class DecomposerError(Exception):
    def __init__(self, failure_mode: str, reason: str | None = None):
        self.failure_mode = failure_mode
        self.reason = reason
        super().__init__(failure_mode)


class RegistryKeyError(Exception):
    pass


class AuditWriteError(Exception):
    pass


class ConfigurationError(Exception):
    pass


class BoundaryError(Exception):
    def __init__(self, failure_mode: str):
        self.failure_mode = failure_mode
        super().__init__(failure_mode)


@dataclass
class SubTask:
    task_type: str
    context: str

    def __post_init__(self) -> None:
        if not self.task_type:
            raise ValueError("task_type must be non-empty")
        if not self.context:
            raise ValueError("context must be non-empty")

    def __repr__(self) -> str:
        return f"SubTask(task_type={self.task_type!r}, context_len={len(self.context)})"


@dataclass
class AgentResult:
    task_type: str
    success: bool
    content: str | None = None
    failure_mode: str | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.success:
            if self.content is None:
                raise ValueError("AgentResult: success=True requires content to be set")
            if self.failure_mode is not None:
                raise ValueError("AgentResult: success=True requires failure_mode to be None")
        else:
            if self.failure_mode is None:
                raise ValueError("AgentResult: success=False requires failure_mode to be set")
            if self.content is not None:
                raise ValueError("AgentResult: success=False requires content to be None")

    def __repr__(self) -> str:
        if self.success:
            return f"AgentResult(task_type={self.task_type!r}, success=True)"
        return f"AgentResult(task_type={self.task_type!r}, success=False, failure_mode={self.failure_mode!r})"


@dataclass
class AuditReport:
    run_id: str
    audit_request: str
    results: list[AgentResult]
    sufficient: bool
    successful_count: int
    failed_count: int
    sufficiency_threshold: int

    def __repr__(self) -> str:
        return (
            f"AuditReport(run_id={self.run_id!r}, sufficient={self.sufficient}, "
            f"successful={self.successful_count}, failed={self.failed_count})"
        )


@dataclass
class AgentConfig:
    temperature: float
    max_tokens: int

    def __post_init__(self) -> None:
        if not (0.0 <= self.temperature <= 1.0):
            raise ValueError(f"temperature must be in [0.0, 1.0], got {self.temperature}")
        if self.max_tokens < 1:
            raise ValueError(f"max_tokens must be >= 1, got {self.max_tokens}")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(temperature={self.temperature}, max_tokens={self.max_tokens})"


@dataclass
class InjectionCheckAgentConfig(AgentConfig):
    pass


@dataclass
class AuthCheckAgentConfig(AgentConfig):
    pass


@dataclass
class XSSCheckAgentConfig(AgentConfig):
    pass


@dataclass
class GenericAuditAgentConfig(AgentConfig):
    pass


@dataclass
class Config:
    llm_base_url: str
    llm_model: str
    llm_api_key: str
    audit_log_path: str
    sufficiency_threshold: int
    max_workers: int
    decomposer_temperature: float
    agent_configs: dict[str, AgentConfig]

    def __repr__(self) -> str:
        return (
            f"Config(llm_model={self.llm_model!r}, "
            f"sufficiency_threshold={self.sufficiency_threshold}, "
            f"max_workers={self.max_workers})"
        )
