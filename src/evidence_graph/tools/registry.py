from collections.abc import Mapping
from enum import StrEnum

from evidence_graph.state.models import CountryCode, IncentiveRecord
from evidence_graph.tools.base import FetchedPage, ResearchToolkit, SearchHit, ToolPolicyError


class ToolName(StrEnum):
    SEARCH = "search"
    FETCH = "fetch"
    EXTRACT = "extract"


NODE_TOOLS: Mapping[str, frozenset[ToolName]] = {
    "planner": frozenset(),
    "researcher": frozenset(ToolName),
    "citation_checker": frozenset(),
    "quality_gate": frozenset(),
    "comparator": frozenset(),
}


class ScopedToolkit:
    """A toolkit view that only exposes the tools the registry grants to one node."""

    def __init__(self, inner: ResearchToolkit, node: str, allowed: frozenset[ToolName]) -> None:
        self._inner = inner
        self._node = node
        self._allowed = allowed

    def _require(self, tool: ToolName) -> None:
        if tool not in self._allowed:
            raise ToolPolicyError(f"node {self._node!r} may not use tool {tool!r}")

    def search(self, query: str, country: CountryCode) -> list[SearchHit]:
        self._require(ToolName.SEARCH)
        return self._inner.search(query, country)

    def fetch(self, url: str, country: CountryCode) -> FetchedPage:
        self._require(ToolName.FETCH)
        return self._inner.fetch(url, country)

    def extract(
        self, page: FetchedPage, country: CountryCode, feedback: str | None = None
    ) -> list[IncentiveRecord]:
        self._require(ToolName.EXTRACT)
        return self._inner.extract(page, country, feedback)

    def hydrate(self, page: FetchedPage) -> FetchedPage:
        hydrate = getattr(self._inner, "hydrate", None)
        return hydrate(page) if hydrate else page

    def set_run_deadline(self, deadline: float | None) -> None:
        setter = getattr(self._inner, "set_run_deadline", None)
        if setter:
            setter(deadline)

    def set_run_id(self, run_id: str | None) -> None:
        setter = getattr(self._inner, "set_run_id", None)
        if setter:
            setter(run_id)


def toolkit_for(node: str, toolkit: ResearchToolkit) -> ScopedToolkit:
    try:
        allowed = NODE_TOOLS[node]
    except KeyError as exc:
        raise ToolPolicyError(f"no tool grant registered for node {node!r}") from exc
    return ScopedToolkit(toolkit, node, allowed)
