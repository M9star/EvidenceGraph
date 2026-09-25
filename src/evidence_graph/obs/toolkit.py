from __future__ import annotations

import time
from threading import local
from typing import TYPE_CHECKING

from evidence_graph.llm.base import take_model_usage
from evidence_graph.obs.cost import CostLedger, UsageEvent, current_run_id
from evidence_graph.obs.tracing import span
from evidence_graph.state.models import CountryCode, IncentiveRecord

if TYPE_CHECKING:
    from evidence_graph.tools.base import FetchedPage, ResearchToolkit, SearchHit


class TracedToolkit:
    """Records a span and a ledger event for every search, fetch, and extract."""

    def __init__(self, inner: ResearchToolkit, ledger: CostLedger) -> None:
        self._inner = inner
        self._ledger = ledger
        self._local = local()

    def set_run_id(self, run_id: str | None) -> None:
        self._local.run_id = run_id

    def set_run_deadline(self, deadline: float | None) -> None:
        setter = getattr(self._inner, "set_run_deadline", None)
        if setter is not None:
            setter(deadline)

    def hydrate(self, page: FetchedPage) -> FetchedPage:
        hydrate = getattr(self._inner, "hydrate", None)
        return hydrate(page) if hydrate else page

    def search(self, query: str, country: CountryCode) -> list[SearchHit]:
        return self._call("search", country, lambda: self._inner.search(query, country))

    def fetch(self, url: str, country: CountryCode) -> FetchedPage:
        return self._call("fetch", country, lambda: self._inner.fetch(url, country), url=url)

    def extract(
        self, page: FetchedPage, country: CountryCode, feedback: str | None = None
    ) -> list[IncentiveRecord]:
        return self._call(
            "extract",
            country,
            lambda: self._inner.extract(page, country, feedback),
            url=page.url,
        )

    def _call(self, kind: str, country: CountryCode, fn, *, url: str | None = None):
        attrs = {"tool": kind, "country": country.value}
        if url:
            attrs["url"] = url
        started = time.perf_counter()
        try:
            with span(f"tool.{kind}", **attrs) as current:
                result = fn()
                usage = take_model_usage() if kind == "extract" else None
                if usage is not None:
                    current.set_attribute("llm.prompt_tokens", usage.prompt_tokens)
                    current.set_attribute("llm.completion_tokens", usage.completion_tokens)
                    current.set_attribute("llm.model", usage.model)
                self._ledger.record(
                    UsageEvent(
                        kind=kind,
                        name=kind,
                        country=country.value,
                        latency_s=time.perf_counter() - started,
                        prompt_tokens=usage.prompt_tokens if usage else 0,
                        completion_tokens=usage.completion_tokens if usage else 0,
                    ),
                    run_id=self._run_id(),
                )
                return result
        except Exception as exc:
            self._ledger.record(
                UsageEvent(
                    kind=kind,
                    name=kind,
                    country=country.value,
                    latency_s=time.perf_counter() - started,
                    ok=False,
                    error=f"{type(exc).__name__}: {exc}",
                ),
                run_id=self._run_id(),
            )
            raise

    def _run_id(self) -> str | None:
        return getattr(self._local, "run_id", None) or current_run_id()
