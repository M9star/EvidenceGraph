from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock
from typing import Protocol


@dataclass(frozen=True)
class ThreadRecord:
    thread_id: str
    user_id: str
    query: str
    created_at: datetime
    updated_at: datetime


class ThreadStore(Protocol):
    def create(self, user_id: str, thread_id: str, query: str) -> ThreadRecord: ...
    def get(self, thread_id: str) -> ThreadRecord | None: ...
    def list_for_user(self, user_id: str) -> list[ThreadRecord]: ...
    def touch(self, thread_id: str, query: str) -> None: ...
    def delete(self, thread_id: str) -> bool: ...


class InMemoryThreadStore:
    def __init__(self) -> None:
        self._records: dict[str, ThreadRecord] = {}
        self._lock = Lock()

    def create(self, user_id: str, thread_id: str, query: str) -> ThreadRecord:
        now = datetime.now(UTC)
        record = ThreadRecord(
            thread_id=thread_id,
            user_id=user_id,
            query=query,
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._records[thread_id] = record
        return record

    def get(self, thread_id: str) -> ThreadRecord | None:
        with self._lock:
            return self._records.get(thread_id)

    def list_for_user(self, user_id: str) -> list[ThreadRecord]:
        with self._lock:
            owned = [r for r in self._records.values() if r.user_id == user_id]
        return sorted(owned, key=lambda r: r.updated_at, reverse=True)

    def touch(self, thread_id: str, query: str) -> None:
        with self._lock:
            current = self._records.get(thread_id)
            if current is None:
                return
            self._records[thread_id] = ThreadRecord(
                thread_id=current.thread_id,
                user_id=current.user_id,
                query=query,
                created_at=current.created_at,
                updated_at=datetime.now(UTC),
            )

    def delete(self, thread_id: str) -> bool:
        with self._lock:
            return self._records.pop(thread_id, None) is not None
