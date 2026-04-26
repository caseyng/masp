from abc import ABC, abstractmethod

from models import SubTask, AgentResult


class LLMCaller:
    """Mixin that owns the LLM provider reference and _call_llm()."""

    _llm = None
    _system_prompt: str = ""

    def _call_llm(self, user_content: str) -> str | None:
        messages = []
        if self._system_prompt:
            messages.append({"role": "system", "content": self._system_prompt})
        messages.append({"role": "user", "content": user_content})
        try:
            response = self._llm.complete(messages)
            if response is None:
                return None
            return response.content
        except Exception:
            return None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"


class BaseAgent(ABC, LLMCaller):
    name: str = ""
    _tools: list = []
    _system_prompt: str = ""

    @abstractmethod
    def execute(self, subtask: SubTask) -> AgentResult:
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"
