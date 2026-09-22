from collections.abc import Mapping

from evidence_graph.state.models import Citation, CountryCode, IncentiveRecord
from evidence_graph.tools.base import FetchedPage, SearchHit, ToolUnavailableError
from evidence_graph.use_cases.ev_incentives.fixtures import FIXTURE_PAGES


class FixtureToolkit:
    """Offline toolkit for tests and local runs. Returns canned pages, never real policy data."""

    def __init__(
        self,
        pages: Mapping[CountryCode, list[FetchedPage]] = FIXTURE_PAGES,
        fail_on: frozenset[CountryCode] = frozenset(),
    ) -> None:
        self._pages = pages
        self._fail_on = fail_on

    def search(self, query: str, country: CountryCode) -> list[SearchHit]:
        if country in self._fail_on:
            raise ToolUnavailableError(f"search unavailable for {country}")
        return [SearchHit(url=page.url, title=page.title) for page in self._pages.get(country, [])]

    def fetch(self, url: str, country: CountryCode) -> FetchedPage:
        for page in self._pages.get(country, []):
            if page.url == url:
                return page
        raise ToolUnavailableError(f"no fixture page for {url}")

    def extract(self, page: FetchedPage, country: CountryCode) -> list[IncentiveRecord]:
        return [
            IncentiveRecord(
                name=page.title,
                benefit="Fixture benefit. Replaced by live extraction in week 2.",
                eligibility=["Fixture rule. Replaced by live extraction in week 2."],
                citations=[
                    Citation(url=page.url, title=page.title, retrieved_at=page.retrieved_at)
                ],
            )
        ]
