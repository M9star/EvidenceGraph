from collections.abc import Mapping
from urllib.parse import urlsplit

from evidence_graph.state.models import CountryCode, IncentiveRecord
from evidence_graph.tools.base import FetchedPage, ResearchToolkit, SearchHit, ToolPolicyError


def is_allowed(url: str, allowed_domains: frozenset[str]) -> bool:
    parts = urlsplit(url)
    if parts.scheme != "https":
        return False
    host = (parts.hostname or "").lower()
    return any(host == domain or host.endswith(f".{domain}") for domain in allowed_domains)


class AllowlistedToolkit:
    """Wraps any toolkit so each country can only reach its own official domains."""

    def __init__(
        self,
        inner: ResearchToolkit,
        allowlists: Mapping[CountryCode, frozenset[str]],
    ) -> None:
        self._inner = inner
        self._allowlists = allowlists

    def _domains(self, country: CountryCode) -> frozenset[str]:
        try:
            return self._allowlists[country]
        except KeyError as exc:
            raise ToolPolicyError(f"no allowlist configured for {country}") from exc

    def search(self, query: str, country: CountryCode) -> list[SearchHit]:
        domains = self._domains(country)
        return [hit for hit in self._inner.search(query, country) if is_allowed(hit.url, domains)]

    def fetch(self, url: str, country: CountryCode) -> FetchedPage:
        if not is_allowed(url, self._domains(country)):
            raise ToolPolicyError(f"{url} is outside the {country} allowlist")
        return self._inner.fetch(url, country)

    def extract(
        self, page: FetchedPage, country: CountryCode, feedback: str | None = None
    ) -> list[IncentiveRecord]:
        if not is_allowed(page.url, self._domains(country)):
            raise ToolPolicyError(f"{page.url} is outside the {country} allowlist")
        return self._inner.extract(page, country, feedback)
