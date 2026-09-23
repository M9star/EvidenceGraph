import json

import httpx
import pytest

from evidence_graph.state import CountryCode
from evidence_graph.tools import ToolUnavailableError
from evidence_graph.tools.search import SeedSearch, TavilySearch
from evidence_graph.use_cases.ev_incentives import allowlists


def tavily(handler) -> TavilySearch:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return TavilySearch("tvly-test", allowlists(), max_results=3, client=client)


def test_tavily_restricts_the_query_to_the_country_allowlist():
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"results": [{"url": "https://www.gov.uk/grant", "title": "Grant"}, {"x": 1}]},
        )

    hits = tavily(handler).search("electric car grant " * 50, CountryCode.UK)

    assert seen["auth"] == "Bearer tvly-test"
    assert seen["body"]["include_domains"] == ["gov.uk"]
    assert seen["body"]["max_results"] == 3
    assert len(seen["body"]["query"]) <= 400
    assert [hit.url for hit in hits] == ["https://www.gov.uk/grant"]


def test_tavily_errors_become_tool_unavailable():
    with pytest.raises(ToolUnavailableError):
        tavily(lambda request: httpx.Response(500)).search("grant", CountryCode.UK)


@pytest.mark.live
def test_tavily_live_returns_https_hits_on_the_uk_allowlist():
    """One real Tavily call. Needs EVIDENCEGRAPH_TAVILY_API_KEY in .env and pytest --live."""
    from evidence_graph.config import Settings
    from evidence_graph.tools import is_allowed

    settings = Settings()
    if settings.tavily_api_key is None:
        pytest.skip("no EVIDENCEGRAPH_TAVILY_API_KEY in .env")

    hits = TavilySearch(
        api_key=settings.tavily_api_key.get_secret_value(),
        allowlists=allowlists(),
        max_results=3,
    ).search("electric car grant", CountryCode.UK)

    assert hits, "Tavily returned no results for the UK allowlist"
    allowed = allowlists()[CountryCode.UK]
    for hit in hits:
        assert is_allowed(hit.url, allowed), hit.url
        assert hit.title


def test_seed_search_returns_hand_verified_pages():
    seeds = SeedSearch({CountryCode.UK: ("https://www.gov.uk/a", "https://www.gov.uk/b")})

    assert [h.url for h in seeds.search("anything", CountryCode.UK)] == [
        "https://www.gov.uk/a",
        "https://www.gov.uk/b",
    ]
    assert seeds.search("anything", CountryCode.DE) == []
