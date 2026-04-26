import json
import os
import urllib.request
import urllib.error


def build_llm_provider(base_url: str, model: str, api_key: str):
    if os.environ.get("USE_MOCK_LLM", "").strip():
        from mock_llm import MockLLMProvider
        return MockLLMProvider()
    return _OpenAICompatibleProvider(base_url, model, api_key)


class _OpenAICompatibleProvider:
    def __init__(self, base_url: str, model: str, api_key: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._api_key = api_key

    def complete(self, messages: list[dict], model: str | None = None) -> object | None:
        url = self._base_url + "/chat/completions"
        payload = json.dumps({
            "model": model or self._model,
            "messages": messages,
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}" if self._api_key else "Bearer none",
        }

        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                content = data["choices"][0]["message"]["content"]
                return _Response(content)
        except Exception:
            return None

    def __repr__(self) -> str:
        return f"OpenAICompatibleProvider(model={self._model!r})"


class _Response:
    def __init__(self, content: str) -> None:
        self.content = content

    def __repr__(self) -> str:
        return f"Response(content_len={len(self.content)})"
