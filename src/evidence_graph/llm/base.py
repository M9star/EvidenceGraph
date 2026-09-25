from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Protocol


class ModelError(Exception):
    pass


@dataclass(frozen=True)
class ModelUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    model: str = ""


_last_usage: ContextVar[ModelUsage | None] = ContextVar("evidencegraph_model_usage", default=None)


def record_model_usage(usage: ModelUsage) -> None:
    _last_usage.set(usage)


def take_model_usage() -> ModelUsage | None:
    usage = _last_usage.get()
    _last_usage.set(None)
    return usage


class StructuredModel(Protocol):
    """Any model that returns a JSON object matching a JSON schema."""

    def generate_json(self, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]: ...
