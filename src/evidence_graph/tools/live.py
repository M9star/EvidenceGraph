from evidence_graph.state.models import CountryCode, IncentiveRecord
from evidence_graph.tools.base import FetchedPage, SearchHit, SearchProvider
from evidence_graph.tools.http_fetch import HttpFetcher
from evidence_graph.tools.llm_extract import LlmExtractor


class LiveToolkit:
    """Real search, real HTTP, real model. Always wrapped by AllowlistedToolkit in build_graph."""

    def __init__(self, search: SearchProvider, fetcher: HttpFetcher, extractor: LlmExtractor):
        self._search = search
        self._fetcher = fetcher
        self._extractor = extractor

    def search(self, query: str, country: CountryCode) -> list[SearchHit]:
        return self._search.search(query, country)

    def fetch(self, url: str, country: CountryCode) -> FetchedPage:
        return self._fetcher.fetch(url, country)

    def extract(
        self, page: FetchedPage, country: CountryCode, feedback: str | None = None
    ) -> list[IncentiveRecord]:
        return self._extractor.extract(page, country, feedback)
