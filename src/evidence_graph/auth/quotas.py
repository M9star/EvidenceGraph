from datetime import UTC, date, datetime
from threading import Lock
from typing import Protocol


class QuotaExceeded(Exception):
    def __init__(self, used: int, limit: int) -> None:
        self.used = used
        self.limit = limit
        super().__init__(f"daily run quota exceeded ({used}/{limit})")


class QuotaStore(Protocol):
    def consume(self, user_id: str, limit: int, day: date | None = None) -> int:
        """Reserve one run for `user_id` today. Raises QuotaExceeded at the limit."""
        ...


class InMemoryQuotaStore:
    def __init__(self) -> None:
        self._used: dict[tuple[str, date], int] = {}
        self._lock = Lock()

    def consume(self, user_id: str, limit: int, day: date | None = None) -> int:
        day = day or datetime.now(UTC).date()
        key = (user_id, day)
        with self._lock:
            used = self._used.get(key, 0)
            if used >= limit:
                raise QuotaExceeded(used, limit)
            used += 1
            self._used[key] = used
            return used
