import json

from base_agent import LLMCaller
from boundary import LLMBoundary
from models import SubTask, DecomposerError

_SYSTEM_PROMPT = (
    "You decompose security audit requests into typed subtasks. "
    "Return a JSON array only — no prose, no markdown, no explanation. "
    "Each item must have exactly two keys: task_type and context. "
    "Valid task types in priority order: injection_check, auth_check, xss_check, generic_audit. "
    "Use generic_audit only when no specific type fits. "
    "Do not return an empty array."
)


class Decomposer(LLMCaller):
    """Plain class. MUST NOT extend BaseAgent."""

    _system_prompt = _SYSTEM_PROMPT

    def __init__(self, llm_provider, temperature: float) -> None:
        self._llm = llm_provider
        self._temperature = temperature

    def decompose(self, audit_request: str) -> list[SubTask]:
        if not audit_request:
            raise ValueError("audit_request must be non-empty")

        boundary = LLMBoundary()

        check = boundary.check_input(audit_request)
        if not check.safe:
            raise DecomposerError(failure_mode=check.failure_mode)

        prompt = (
            f"Decompose this security audit request into typed subtasks.\n\n"
            f"Request: {audit_request}"
        )

        response = self._call_llm(prompt)
        if response is None:
            raise DecomposerError(failure_mode="decomposer_llm_unavailable")

        check = boundary.check_output(response)
        if not check.safe:
            raise DecomposerError(failure_mode=check.failure_mode)

        try:
            items = json.loads(response)
            if not isinstance(items, list):
                raise DecomposerError(failure_mode="decomposer_output_unparseable")
            subtasks = [
                SubTask(task_type=str(i["task_type"]), context=str(i["context"]))
                for i in items
            ]
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            raise DecomposerError(failure_mode="decomposer_output_unparseable")

        if not subtasks:
            raise DecomposerError(failure_mode="decomposer_output_unparseable")

        return subtasks

    def __repr__(self) -> str:
        return f"Decomposer(temperature={self._temperature})"
