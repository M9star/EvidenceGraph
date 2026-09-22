from evidence_graph.graph import run_comparison
from evidence_graph.state import CountryCode, ReportStatus

ALL = [CountryCode.FR, CountryCode.DE, CountryCode.UK, CountryCode.IN]


def test_every_country_is_researched_and_merged_in_request_order(graph, settings, query):
    comparison = run_comparison(graph, settings, query, ALL, thread_id="t-fan-out")

    assert [report.country for report in comparison.reports] == ALL
    assert all(report.status is ReportStatus.OK for report in comparison.reports)
    assert comparison.missing == []


def test_every_incentive_carries_a_citation(graph, settings, query):
    comparison = run_comparison(graph, settings, query, ALL, thread_id="t-citations")

    for report in comparison.reports:
        assert report.incentives
        for incentive in report.incentives:
            assert incentive.citations


def test_subset_of_countries_only_runs_those(graph, settings, query):
    subset = [CountryCode.UK, CountryCode.FR]
    comparison = run_comparison(graph, settings, query, subset, thread_id="t-subset")

    assert [report.country for report in comparison.reports] == subset


def test_duplicate_countries_are_researched_once(graph, settings, query):
    requested = [CountryCode.DE, CountryCode.DE, CountryCode.IN]
    comparison = run_comparison(graph, settings, query, requested, thread_id="t-dedupe")

    assert [report.country for report in comparison.reports] == [CountryCode.DE, CountryCode.IN]
