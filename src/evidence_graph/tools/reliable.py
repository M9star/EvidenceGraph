import time
from collections.abc import Callable
from threading import Lock
from typing import TypeVar
from urllib.parse import urlsplit, urlunsplit

from evidence_graph.graph.policies import ReliabilityPolicy
from evidence_graph.state.models import CountryCode, IncentiveRecord
from evidence_graph.tools.base import (
    FetchedPage,
    ResearchToolkit,
    SearchHit,
    ToolError,
    ToolPolicyError,
    ToolUnavailableError,
)

T = TypeVar("T")


class BudgetExceeded(ToolUnavailableError):
    """This researcher has used its tool-call budget for the run."""


def fingerprint_url(url: str) -> str:
    parts = urlsplit(url)
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), (parts.netloc or "").lower(), path, parts.query, ""))


class ReliableToolkit:
    """Retry transient errors, cap calls, and reuse fetches for the same URL.

    Policy errors are never retried. Cache hits do not charge the budget.
    """

    def __init__(
        self,
        inner: ResearchToolkit,
        policy: ReliabilityPolicy,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
        run_deadline: float | None = None,
    ) -> None:
        self._inner = inner
        self._policy = policy
        self._clock = clock
        self._sleep = sleeper
        self._run_deadline = run_deadline
        self._lock = Lock()
        self._calls: dict[CountryCode, int] = {}
        self._country_deadline: dict[CountryCode, float] = {}
        self._pages: dict[tuple[CountryCode, str], FetchedPage] = {}

    def set_run_deadline(self, deadline: float | None) -> None:
        with self._lock:
            self._run_deadline = deadline

    def search(self, query: str, country: CountryCode) -> list[SearchHit]:
        return self._call(country, lambda: self._inner.search(query, country))

    def fetch(self, url: str, country: CountryCode) -> FetchedPage:
        key = (country, fingerprint_url(url))
        with self._lock:
            cached = self._pages.get(key)
        if cached is not None:
            return cached
        page = self._call(country, lambda: self._inner.fetch(url, country))
        with self._lock:
            self._pages[key] = page
        return page

    def extract(
        self, page: FetchedPage, country: CountryCode, feedback: str | None = None
    ) -> list[IncentiveRecord]:
        return self._call(country, lambda: self._inner.extract(page, country, feedback))

    def hydrate(self, page: FetchedPage) -> FetchedPage:
        hydrate = getattr(self._inner, "hydrate", None)
        return hydrate(page) if hydrate else page

    def _call(self, country: CountryCode, fn: Callable[[], T]) -> T:
        self._charge(country)
        timeout_s = self._remaining_tool_timeout(country)
        delay = self._policy.retry_backoff_s
        last: ToolUnavailableError | None = None
        attempts = self._policy.max_retries + 1
        for attempt in range(attempts):
            try:
                return self._invoke(fn, timeout_s)
            except ToolPolicyError:
                raise
            except ToolUnavailableError as exc:
                last = exc
                if attempt + 1 == attempts:
                    raise
                if delay:
                    self._sleep(delay)
                    delay *= 2
            except ToolError:
                raise
        assert last is not None
        raise last

    def _invoke(self, fn: Callable[[], T], timeout_s: float) -> T:
        started = self._clock()
        result = fn()
        if self._clock() - started > timeout_s:
            raise ToolUnavailableError(f"tool timed out after {timeout_s:.3f}s")
        return result

    def _charge(self, country: CountryCode) -> None:
        now = self._clock()
        with self._lock:
            deadline = self._country_deadline.setdefault(
                country, now + self._policy.country_timeout_s
            )
            used = self._calls.get(country, 0)
            if self._run_deadline is not None and now >= self._run_deadline:
                raise ToolUnavailableError("run deadline reached")
            if now >= deadline:
                raise ToolUnavailableError("country deadline reached")
            if used >= self._policy.max_tool_calls:
                raise BudgetExceeded(
                    f"{country} used {used} tool calls (limit {self._policy.max_tool_calls})"
                )
            self._calls[country] = used + 1

    def _remaining_tool_timeout(self, country: CountryCode) -> float:
        now = self._clock()
        remaining = [self._policy.tool_timeout_s]
        with self._lock:
            country_deadline = self._country_deadline.get(country)
        if country_deadline is not None:
            remaining.append(country_deadline - now)
        if self._run_deadline is not None:
            remaining.append(self._run_deadline - now)
        return max(min(remaining), 0.0)
