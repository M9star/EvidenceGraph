import pytest

from evidence_graph.graph import build_graph, run_comparison
from evidence_graph.state import CountryCode, ReportStatus
from evidence_graph.tools import AllowlistedToolkit, SearchHit, ToolPolicyError, is_allowed
from evidence_graph.tools.fixture import FixtureToolkit
from evidence_graph.use_cases.ev_incentives import allowlists

GOV_UK = frozenset({"gov.uk"})


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.gov.uk/plug-in-vehicle-grants", True),
        ("https://gov.uk/", True),
        ("http://www.gov.uk/", False),
        ("https://gov.uk.evil.example/", False),
        ("https://notgov.uk/", False),
        ("https://example.com/?next=gov.uk", False),
    ],
)
def test_is_allowed(url, expected):
    assert is_allowed(url, GOV_UK) is expected


class LeakyToolkit(FixtureToolkit):
    def search(self, query, country):
        return [SearchHit(url="https://blog.example.com/ev-deals", title="Unofficial blog")]


def test_off_allowlist_search_hits_are_dropped():
    guarded = AllowlistedToolkit(LeakyToolkit(), allowlists())

    assert guarded.search("ev grants", CountryCode.UK) == []


def test_fetch_outside_the_country_allowlist_is_refused():
    guarded = AllowlistedToolkit(FixtureToolkit(), allowlists())

    with pytest.raises(ToolPolicyError):
        guarded.fetch("https://www.bafa.de/", CountryCode.UK)


def test_leaky_search_never_produces_uncited_or_off_list_evidence(settings, query):
    graph = build_graph(LeakyToolkit(), settings)

    comparison = run_comparison(graph, settings, query, [CountryCode.UK], thread_id="t-leaky")

    assert comparison.reports[0].status is ReportStatus.INSUFFICIENT_EVIDENCE
    assert comparison.reports[0].incentives == []
