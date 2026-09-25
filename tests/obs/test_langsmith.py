import os

from evidence_graph.config import Settings
from evidence_graph.obs.langsmith import configure_langsmith


def test_langsmith_stays_off_without_a_key(monkeypatch):
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    settings = Settings(_env_file=None, langsmith_api_key=None)

    assert configure_langsmith(settings) is False
    assert os.environ.get("LANGCHAIN_TRACING_V2") is None


def test_langsmith_sets_env_when_a_key_is_present(monkeypatch):
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    monkeypatch.delenv("LANGCHAIN_PROJECT", raising=False)
    settings = Settings(
        _env_file=None,
        langsmith_api_key="example-not-a-real-langsmith-key",
        langsmith_project="eg-test",
    )

    assert configure_langsmith(settings) is True
    assert os.environ["LANGCHAIN_TRACING_V2"] == "true"
    assert os.environ["LANGCHAIN_API_KEY"] == "example-not-a-real-langsmith-key"
    assert os.environ["LANGCHAIN_PROJECT"] == "eg-test"
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
