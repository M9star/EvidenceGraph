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


def test_seed_search_returns_hand_verified_pages():
    seeds = SeedSearch({CountryCode.UK: ("https://www.gov.uk/a", "https://www.gov.uk/b")})

    assert [h.url for h in seeds.search("anything", CountryCode.UK)] == [
        "https://www.gov.uk/a",
        "https://www.gov.uk/b",
    ]
    assert seeds.search("anything", CountryCode.DE) == []
