from contextvars import ContextVar
from dataclasses import dataclass, field
from threading import Lock
from uuid import uuid4

from evidence_graph.config import Settings

_current_run: ContextVar[str | None] = ContextVar("evidencegraph_run_id", default=None)


@dataclass(frozen=True)
class CostRates:
    search_usd: float = 0.008
    fetch_usd: float = 0.0
    prompt_token_usd: float = 0.0
    completion_token_usd: float = 0.0

    @classmethod
    def from_settings(cls, settings: Settings) -> "CostRates":
        return cls(
            search_usd=settings.search_cost_usd,
            fetch_usd=settings.fetch_cost_usd,
            prompt_token_usd=settings.prompt_token_usd,
            completion_token_usd=settings.completion_token_usd,
        )


@dataclass(frozen=True)
class UsageEvent:
    kind: str
    name: str
    country: str | None
    latency_s: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    ok: bool = True
    error: str | None = None


@dataclass
class RunCost:
    run_id: str
    user_id: str = "anonymous"
    thread_id: str = ""
    events: list[UsageEvent] = field(default_factory=list)
    latency_s: float = 0.0

    @property
    def tool_calls(self) -> int:
        return sum(1 for event in self.events if event.kind in {"search", "fetch", "extract"})

    @property
    def tokens(self) -> int:
        return sum(event.prompt_tokens + event.completion_tokens for event in self.events)

    def estimated_usd(self, rates: CostRates) -> float:
        total = 0.0
        for event in self.events:
            if event.kind == "search":
                total += rates.search_usd
            elif event.kind == "fetch":
                total += rates.fetch_usd
            total += event.prompt_tokens * rates.prompt_token_usd
            total += event.completion_tokens * rates.completion_token_usd
        return round(total, 6)

    def summary(self, rates: CostRates) -> dict[str, float | int | str]:
        return {
            "run_id": self.run_id,
            "latency_s": round(self.latency_s, 3),
            "tool_calls": self.tool_calls,
            "tokens": self.tokens,
            "estimated_usd": self.estimated_usd(rates),
        }


class CostLedger:
    """In-process ledger. One instance is shared; events are keyed by run_id."""

    def __init__(self, rates: CostRates | None = None) -> None:
        self.rates = rates or CostRates()
        self._runs: dict[str, RunCost] = {}
        self._lock = Lock()

    @classmethod
    def from_settings(cls, settings: Settings) -> "CostLedger":
        return cls(CostRates.from_settings(settings))

    def start(
        self,
        *,
        user_id: str,
        thread_id: str,
        run_id: str | None = None,
    ) -> RunCost:
        run_id = run_id or str(uuid4())
        run = RunCost(run_id=run_id, user_id=user_id, thread_id=thread_id)
        with self._lock:
            self._runs[run_id] = run
        _current_run.set(run_id)
        return run

    def record(self, event: UsageEvent, run_id: str | None = None) -> None:
        run_id = run_id or _current_run.get()
        if run_id is None:
            return
        with self._lock:
            run = self._runs.get(run_id)
            if run is not None:
                run.events.append(event)

    def finish(self, run_id: str | None = None, *, latency_s: float = 0.0) -> RunCost | None:
        run_id = run_id or _current_run.get()
        if run_id is None:
            return None
        with self._lock:
            run = self._runs.get(run_id)
            if run is not None:
                run.latency_s = latency_s
            return run

    def get(self, run_id: str) -> RunCost | None:
        return self._runs.get(run_id)


def current_run_id() -> str | None:
    return _current_run.get()
