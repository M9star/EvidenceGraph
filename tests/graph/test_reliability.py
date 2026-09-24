import time
from datetime import UTC, datetime

from evidence_graph.graph import ReliabilityPolicy, build_graph, run_comparison
from evidence_graph.memory.reports import InMemoryReportCache
from evidence_graph.state import Citation, CountryCode, CountryReport, IncentiveRecord, ReportStatus
from evidence_graph.tools.fixture import FixtureToolkit
from evidence_graph.use_cases.ev_incentives.fixtures import FIXTURE_PAGES

UK = CountryCode.UK
UK_PAGE = FIXTURE_PAGES[UK][0]


class DuplicateHitToolkit(FixtureToolkit):
    """Same official URL three times — the URL cache must fetch it once."""

    def __init__(self) -> None:
        super().__init__()
        self.fetches = 0

    def search(self, query, country):
        hit = super().search(query, country)[0]
        return [hit, hit, hit]

    def fetch(self, url, country):
        self.fetches += 1
        return super().fetch(url, country)


class SlowSearchToolkit(FixtureToolkit):
    def search(self, query, country):
        time.sleep(0.04)
        return super().search(query, country)


def test_repeated_urls_are_fetched_once(settings, query):
    inner = DuplicateHitToolkit()
    graph = build_graph(inner, settings)

    run_comparison(graph, settings, query, [UK], thread_id="t-dedupe-url")

    assert inner.fetches == 1


def test_slow_country_degrades_instead_of_hanging(settings, query):
    tight = settings.model_copy(update={"tool_timeout_s": 0.01, "tool_retries": 0})
    graph = build_graph(SlowSearchToolkit(), tight, policy=ReliabilityPolicy.from_settings(tight))

    comparison = run_comparison(graph, tight, query, [UK], thread_id="t-slow")

    assert comparison.missing == [UK]
    assert "timed out" in (comparison.reports[0].error or "")


def test_last_good_report_is_used_when_the_country_fails(settings, query):
    cached = CountryReport(
        country=UK,
        status=ReportStatus.OK,
        incentives=[
            IncentiveRecord(
                name="Cached grant",
                benefit="Fixture benefit. Not real policy data.",
                eligibility=["Fixture rule. Not real policy data."],
                citations=[
                    Citation(
                        url=UK_PAGE.url,
                        title=UK_PAGE.title,
                        retrieved_at=datetime(2026, 9, 1, tzinfo=UTC),
                        quote=UK_PAGE.text,
                    )
                ],
            )
        ],
    )
    cache = InMemoryReportCache()
    cache.put(cached)
    graph = build_graph(
        FixtureToolkit(fail_on=frozenset({UK})),
        settings,
        report_cache=cache,
        policy=ReliabilityPolicy(max_retries=0, retry_backoff_s=0),
    )

    comparison = run_comparison(graph, settings, query, [UK], thread_id="t-fallback")

    assert comparison.missing == []
    assert comparison.reports[0].status is ReportStatus.OK
    assert comparison.reports[0].incentives[0].name == "Cached grant"
    assert any(
        "fallback: last-good UK report from 2026-09-01" in warning
        for warning in comparison.reports[0].warnings
    )


def test_old_turns_are_summarized_on_a_reused_thread(settings, query):
    graph = build_graph(
        FixtureToolkit(),
        settings,
        policy=ReliabilityPolicy(history_keep_recent=2),
    )
    for _ in range(5):
        run_comparison(graph, settings, query, [UK], thread_id="t-summarize")

    snapshot = graph.get_state({"configurable": {"thread_id": "t-summarize"}})
    assert len(snapshot.values["history"]) == 2
    assert len(snapshot.values["history_summaries"]) == 2
    assert all("UK ok" in line for line in snapshot.values["history_summaries"])
