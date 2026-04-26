from base_agent import BaseAgent, LLMCaller
from boundary import LLMBoundary
from models import SubTask, AgentResult, InjectionCheckAgentConfig
from tools import scan_injection_patterns, check_parameterised_queries


class InjectionCheckAgent(BaseAgent):
    name = "injection_check"
    _system_prompt = (
        "You are a SQL and command injection security auditor. "
        "Given a description of code or an endpoint, identify injection vulnerabilities. "
        "Report: vulnerability type, affected input, severity (high/medium/low), brief explanation. "
        "If no vulnerabilities found, say so explicitly."
    )
    _tools = [scan_injection_patterns, check_parameterised_queries]

    def __init__(self, subtask: SubTask, config: InjectionCheckAgentConfig, llm_provider) -> None:
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
            return AgentResult(
                task_type=subtask.task_type,
                success=False,
                failure_mode="agent_execution_error",
            )
