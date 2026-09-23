from pathlib import Path

from evidence_graph.graph import build_graph, run_comparison
from evidence_graph.graph.nodes.citations import check_record
from evidence_graph.state import CountryCode, ReportStatus
from evidence_graph.tools import is_allowed
from evidence_graph.tools.fixture import FixtureToolkit
from evidence_graph.tools.recording import RecordingToolkit, ReplayToolkit, load_recording
from evidence_graph.use_cases.ev_incentives import allowlists

RECORDED = Path(__file__).parents[1] / "fixtures" / "recorded"
ALL = [CountryCode.FR, CountryCode.DE, CountryCode.UK, CountryCode.IN]


def test_recorded_live_run_replays_offline_with_every_claim_supported(settings, query):
    graph = build_graph(ReplayToolkit(RECORDED), settings)

    comparison = run_comparison(graph, settings, query, ALL, thread_id="t-replay")

    assert comparison.missing == []
    for report in comparison.reports:
        assert report.status is ReportStatus.OK, report.country
        pages = {p.url: p for p in load_recording(RECORDED, report.country).pages}
        for incentive in report.incentives:
            for citation in incentive.citations:
                assert is_allowed(str(citation.url), allowlists()[report.country])
            assert check_record(incentive, pages[str(incentive.citations[0].url)]) == []


def test_replay_reproduces_the_checker_rejecting_hallucinated_quotes(settings, query):
    graph = build_graph(ReplayToolkit(RECORDED), settings)

    comparison = run_comparison(graph, settings, query, [CountryCode.DE], thread_id="t-de")

    assert any("quote not found" in warning for warning in comparison.reports[0].warnings)


def test_recording_then_replaying_gives_the_same_comparison(tmp_path, settings, query):
    recorded_graph = build_graph(RecordingToolkit(FixtureToolkit(), tmp_path), settings)
    live = run_comparison(recorded_graph, settings, query, ALL, thread_id="t-rec")

    replayed_graph = build_graph(ReplayToolkit(tmp_path), settings)
    replayed = run_comparison(replayed_graph, settings, query, ALL, thread_id="t-rep")

    assert replayed == live
