import logging

from base_agent import BaseAgent
from boundary import LLMBoundary
from models import SubTask, AgentResult, XSSCheckAgentConfig
from tools import scan_xss_patterns

logger = logging.getLogger(__name__)


class XSSCheckAgent(BaseAgent):
    name = "xss_check"
    _system_prompt = (
        "You are a cross-site scripting (XSS) security auditor. "
        "Given a description of code or an endpoint, identify reflected, stored, and DOM-based XSS. "
        "Report: XSS type, input vector, output context, severity (high/medium/low), brief explanation. "
        "If no vulnerabilities found, say so explicitly."
    )
    _tools = [scan_xss_patterns]

    def __init__(self, config: XSSCheckAgentConfig, llm_provider) -> None:
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

            tool_context = ""
            for tool in self._tools:
                try:
                    tool_context += "\n" + tool(subtask.context)
                except Exception:
                    return AgentResult(
                        task_type=subtask.task_type,
                        success=False,
                        failure_mode="agent_tool_failed",
                    )

            prompt = subtask.context
            if tool_context.strip():
                prompt += f"\n\nTool findings:\n{tool_context.strip()}"

            response = self._call_llm(prompt)
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
            logger.exception("Unhandled error in XSSCheckAgent.execute")
            return AgentResult(
                task_type=subtask.task_type,
                success=False,
                failure_mode="agent_execution_error",
            )
