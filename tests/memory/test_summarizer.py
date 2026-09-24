from evidence_graph.memory.summarizer import split_history, summarize_comparison
from evidence_graph.state import Comparison, CountryCode, CountryReport, ReportStatus


def _comparison(query: str, country: CountryCode = CountryCode.UK) -> Comparison:
    report = CountryReport(country=country, status=ReportStatus.OK)
    return Comparison(query=query, reports=[report], missing=[])


def test_summarize_comparison_is_one_line():
    text = summarize_comparison(_comparison("What are the EV grants in the UK today?"))

    assert "UK ok (0 incentives)" in text
    assert "missing=none" in text


def test_split_history_keeps_recent_turns_raw():
    history = [_comparison(f"q{i}") for i in range(5)]

    summaries, recent = split_history(history, keep_recent=2)

    assert len(summaries) == 3
    assert [item.query for item in recent] == ["q3", "q4"]
    assert split_history(history[:2], keep_recent=2) == ([], history[:2])
