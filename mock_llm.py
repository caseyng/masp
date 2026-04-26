# mock_llm.py — place at project root, commit in git before challenge starts
import json
import random
from dataclasses import dataclass

@dataclass(frozen=True)
class MockResponse:
    content: str

class MockLLMProvider:
    """Deterministic mock for when no LLM endpoint is available.
    Returns structured SubTask JSON for decomposer, domain-appropriate responses for agents.
    """
    _decomposer_template = '[{"task_type": "%s", "context": "%s"}]'
    _agent_responses = {
        "injection_check": "No SQL injection detected. All queries use parameterized statements.",
        "auth_check": "Authentication uses JWT with 15-minute expiry. No session fixation detected.",
        "xss_check": "No reflected XSS found. Output is HTML-escaped.",
        "generic_audit": "General security posture reviewed. No critical findings.",
    }
    
    def __init__(self, seed: int = 42):
        self._rng = random.Random(seed)
    
    def complete(self, messages: list[dict], model: str | None = None) -> MockResponse | None:
        """Mimics LLM provider interface. Inspects prompt to route response."""
        prompt = " ".join(m.get("content", "") for m in messages)
        
        # Decomposer detection: prompt asks for JSON decomposition
        if "JSON" in prompt and "task_type" in prompt:
            # Extract audit request from prompt (last user message)
            request = messages[-1].get("content", "") if messages else "audit login"
            task_types = ["injection_check", "auth_check", "xss_check", "generic_audit"]
            # Simple keyword match for demo realism
            selected = []
            if any(k in request.lower() for k in ["inject", "sql", "query"]):
                selected.append("injection_check")
            if any(k in request.lower() for k in ["auth", "login", "session"]):
                selected.append("auth_check")
            if any(k in request.lower() for k in ["xss", "script", "html"]):
                selected.append("xss_check")
            if not selected:
                selected.append("generic_audit")
            
            tasks = [{"task_type": t, "context": request} for t in selected]
            return MockResponse(content=json.dumps(tasks))
        
        # Agent detection: check for system prompt domain hints
        for task_type, response in self._agent_responses.items():
            if task_type.replace("_", " ") in prompt.lower() or task_type in prompt.lower():
                return MockResponse(content=response)
        
        # Fallback
        return MockResponse(content="Audit completed. No findings.")
