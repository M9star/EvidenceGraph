from evidence_graph.graph import build_graph, run_comparison
from evidence_graph.state import CountryCode, ReportStatus
from evidence_graph.tools.fixture import FixtureToolkit

ALL = [CountryCode.FR, CountryCode.DE, CountryCode.UK, CountryCode.IN]


def test_one_failed_country_does_not_fail_the_run(settings, query):
    graph = build_graph(FixtureToolkit(fail_on=frozenset({CountryCode.DE})), settings)

    comparison = run_comparison(graph, settings, query, ALL, thread_id="t-partial")

    by_country = {report.country: report for report in comparison.reports}
    assert by_country[CountryCode.DE].status is ReportStatus.INSUFFICIENT_EVIDENCE
    assert "ToolUnavailableError" in (by_country[CountryCode.DE].error or "")
    assert by_country[CountryCode.DE].incentives == []
    for code in (CountryCode.FR, CountryCode.UK, CountryCode.IN):
        assert by_country[code].status is ReportStatus.OK
    assert comparison.missing == [CountryCode.DE]


def test_every_country_failing_still_returns_a_comparison(settings, query):
    graph = build_graph(FixtureToolkit(fail_on=frozenset(ALL)), settings)

    comparison = run_comparison(graph, settings, query, ALL, thread_id="t-all-fail")

    assert comparison.missing == ALL
    assert all(r.status is ReportStatus.INSUFFICIENT_EVIDENCE for r in comparison.reports)
