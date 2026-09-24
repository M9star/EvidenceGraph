import hashlib
from threading import Lock
from typing import Protocol


class ArtifactStore(Protocol):
    def put(self, content: str) -> str:
        """Store `content` and return a stable content hash."""
        ...

    def get(self, digest: str) -> str | None: ...


class InMemoryArtifactStore:
    def __init__(self) -> None:
        self._items: dict[str, str] = {}
        self._lock = Lock()

    def put(self, content: str) -> str:
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        with self._lock:
            self._items[digest] = content
        return digest

    def get(self, digest: str) -> str | None:
        with self._lock:
            return self._items.get(digest)
