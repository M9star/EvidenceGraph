from evidence_graph.graph import run_comparison
from evidence_graph.state import CountryCode

FR_DE = [CountryCode.FR, CountryCode.DE]
UK_IN = [CountryCode.UK, CountryCode.IN]


def test_reusing_a_thread_resets_reports_and_archives_the_previous_comparison(
    graph, settings, query
):
    first = run_comparison(graph, settings, query, FR_DE, thread_id="t-reuse")
    second = run_comparison(graph, settings, query, UK_IN, thread_id="t-reuse")

    assert [report.country for report in first.reports] == FR_DE
    assert [report.country for report in second.reports] == UK_IN

    snapshot = graph.get_state({"configurable": {"thread_id": "t-reuse"}})
    assert [report.country for report in snapshot.values["reports"]] == UK_IN
    history = snapshot.values["history"]
    assert len(history) == 1
    assert [report.country for report in history[0].reports] == FR_DE
