from collections.abc import Mapping

import httpx

from evidence_graph.state.models import CountryCode
from evidence_graph.tools.base import SearchHit, ToolUnavailableError

TAVILY_URL = "https://api.tavily.com/search"
TAVILY_MAX_QUERY_CHARS = 400


class TavilySearch:
    """Web search restricted at query time to each country's allowlisted domains."""

    def __init__(
        self,
        api_key: str,
        allowlists: Mapping[CountryCode, frozenset[str]],
        max_results: int = 5,
        timeout_s: float = 20.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key
        self._allowlists = allowlists
        self._max_results = max_results
        self._client = client or httpx.Client(timeout=timeout_s)

    def search(self, query: str, country: CountryCode) -> list[SearchHit]:
        payload = {
            "query": query[:TAVILY_MAX_QUERY_CHARS],
            "max_results": self._max_results,
            "search_depth": "basic",
            "include_domains": sorted(self._allowlists.get(country, frozenset())),
        }
        try:
            response = self._client.post(
                TAVILY_URL,
                json=payload,
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
            response.raise_for_status()
            results = response.json().get("results", [])
        except (httpx.HTTPError, ValueError) as exc:
            raise ToolUnavailableError(f"tavily search failed: {type(exc).__name__}") from exc
        return [
            SearchHit(url=item["url"], title=item.get("title") or item["url"])
            for item in results
            if item.get("url")
        ]


class SeedSearch:
    """Keyless fallback: returns hand-verified official pages for each country."""

    def __init__(self, seeds: Mapping[CountryCode, tuple[str, ...]]) -> None:
        self._seeds = seeds

    def search(self, query: str, country: CountryCode) -> list[SearchHit]:
        return [SearchHit(url=url, title=url) for url in self._seeds.get(country, ())]
