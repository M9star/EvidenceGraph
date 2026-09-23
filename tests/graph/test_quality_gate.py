from evidence_graph.graph import build_graph, run_comparison
from evidence_graph.graph.nodes.quality_gate import extract_with_gate
from evidence_graph.state import Citation, CountryCode, IncentiveRecord, ReportStatus
from evidence_graph.tools.fixture import FixtureToolkit
from evidence_graph.use_cases.ev_incentives.fixtures import FIXTURE_PAGES

UK_PAGE = FIXTURE_PAGES[CountryCode.UK][0]


def cited(benefit: str, quote: str) -> IncentiveRecord:
    return IncentiveRecord(
        name="Grant",
        benefit=benefit,
        eligibility=[],
        citations=[
            Citation(
                url=UK_PAGE.url,
                title=UK_PAGE.title,
                retrieved_at=UK_PAGE.retrieved_at,
                quote=quote,
            )
        ],
    )


GOOD = cited("Fixture benefit", UK_PAGE.text)
FABRICATED = cited("Up to £9,999", "The grant is £9,999.")


class ScriptedToolkit(FixtureToolkit):
    """Returns a scripted extraction per attempt and records the feedback it was given."""

    def __init__(self, attempts: list[list[IncentiveRecord]]) -> None:
        super().__init__()
        self.attempts = attempts
        self.feedback: list[str | None] = []

    def extract(self, page, country, feedback=None):
        self.feedback.append(feedback)
        return self.attempts[min(len(self.feedback), len(self.attempts)) - 1]


def test_clean_extraction_is_accepted_without_retry():
    toolkit = ScriptedToolkit([[GOOD]])

    result = extract_with_gate(toolkit, UK_PAGE, CountryCode.UK, max_attempts=2)

    assert result.accepted == [GOOD]
    assert result.score == 1.0
    assert toolkit.feedback == [None]


def test_rejected_extraction_is_retried_once_with_the_checker_feedback():
    toolkit = ScriptedToolkit([[FABRICATED], [GOOD]])

    result = extract_with_gate(toolkit, UK_PAGE, CountryCode.UK, max_attempts=2)

    assert result.accepted == [GOOD]
    assert toolkit.feedback[0] is None
    assert "quote not found" in (toolkit.feedback[1] or "")


def test_retry_is_bounded_and_keeps_only_supported_records():
    toolkit = ScriptedToolkit([[FABRICATED, GOOD]])

    result = extract_with_gate(toolkit, UK_PAGE, CountryCode.UK, max_attempts=2)

    assert len(toolkit.feedback) == 2
    assert result.accepted == [GOOD]
    assert result.rejected == 1
    assert result.score == 0.5


def test_country_with_only_fabricated_claims_degrades_and_explains_why(settings, query):
    graph = build_graph(ScriptedToolkit([[FABRICATED]]), settings)

    comparison = run_comparison(graph, settings, query, [CountryCode.UK], thread_id="t-gate")

    report = comparison.reports[0]
    assert report.status is ReportStatus.INSUFFICIENT_EVIDENCE
    assert report.incentives == []
    assert any("quote not found" in warning for warning in report.warnings)
    assert comparison.missing == [CountryCode.UK]
