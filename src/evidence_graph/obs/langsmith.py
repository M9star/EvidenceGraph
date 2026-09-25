import os

from evidence_graph.config import Settings


def configure_langsmith(settings: Settings) -> bool:
    """Turn on LangGraph's LangSmith tracer when a key is configured. No-op otherwise."""
    if settings.langsmith_api_key is None:
        return False
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGSMITH_TRACING", "true")
    os.environ.setdefault("LANGCHAIN_API_KEY", settings.langsmith_api_key.get_secret_value())
    os.environ.setdefault("LANGCHAIN_PROJECT", settings.langsmith_project)
    return True
