import json

import httpx
import pytest

from evidence_graph.llm import ModelError, OllamaModel


def model(handler) -> OllamaModel:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return OllamaModel("http://ollama.test/", "llama3.1:8b", num_ctx=8192, client=client)


def test_sends_schema_and_context_window_and_parses_json():
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"message": {"content": '{"incentives": []}'}})

    result = model(handler).generate_json("sys", "user", {"type": "object"})

    assert result == {"incentives": []}
    assert seen["url"] == "http://ollama.test/api/chat"
    assert seen["body"]["format"] == {"type": "object"}
    assert seen["body"]["stream"] is False
    assert seen["body"]["options"] == {"temperature": 0, "num_ctx": 8192}


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(500),
        httpx.Response(200, json={"message": {"content": "not json"}}),
        httpx.Response(200, json={"message": {"content": "[1, 2]"}}),
        httpx.Response(200, json={"unexpected": True}),
    ],
)
def test_bad_responses_raise_model_error(response):
    with pytest.raises(ModelError):
        model(lambda request: response).generate_json("sys", "user", {})
