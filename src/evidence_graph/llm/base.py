from typing import Any, Protocol


class ModelError(Exception):
    pass


class StructuredModel(Protocol):
    """Any model that returns a JSON object matching a JSON schema."""

    def generate_json(self, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]: ...
