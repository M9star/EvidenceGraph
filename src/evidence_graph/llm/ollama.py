import json
from typing import Any

import httpx

from evidence_graph.llm.base import ModelError


class OllamaModel:
    """Local model via Ollama's /api/chat with schema-constrained JSON output."""

    def __init__(
        self,
        base_url: str,
        model: str,
        num_ctx: int = 8192,
        timeout_s: float = 180.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._url = f"{base_url.rstrip('/')}/api/chat"
        self._model = model
        self._num_ctx = num_ctx
        self._client = client or httpx.Client(timeout=timeout_s)

    def generate_json(self, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "format": schema,
            # Ollama's default context window silently truncates long pages.
            "options": {"temperature": 0, "num_ctx": self._num_ctx},
        }
        try:
            response = self._client.post(self._url, json=payload)
            response.raise_for_status()
            content = response.json()["message"]["content"]
            result = json.loads(content)
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise ModelError(f"ollama {self._model}: {type(exc).__name__}: {exc}") from exc
        if not isinstance(result, dict):
            raise ModelError(f"ollama {self._model}: expected a JSON object")
        return result
