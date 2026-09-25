from datetime import UTC, datetime

from evidence_graph.evals.gate import DEFAULT_THRESHOLDS, gate
from evidence_graph.evals.goldens import FIXTURE_CASE, REPLAY_CASE, ExpectedFact, GoldenCase
from evidence_graph.evals.graders import grade_all, grade_citations, grade_facts, quote_problems
from evidence_graph.evals.runner import EvalResult, run_case
from evidence_graph.state import (
    Citation,
    Comparison,
    CountryCode,
    CountryReport,
    IncentiveRecord,
    ReportStatus,
)


def _record(benefit: str, quote: str | None, name: str = "Grant") -> IncentiveRecord:
    return IncentiveRecord(
        name=name,
        benefit=benefit,
        eligibility=[],
        citations=[
            Citation(
                url="https://www.gov.uk/",
                title="t",
                retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
                quote=quote,
            )
        ],
    )


def test_quote_grounding_rejects_a_benefit_number_missing_from_quotes():
    bad = _record("Up to £3,750", "The seller includes it as a discount")
    good = _record("Up to £3,750", "The maximum discount is £3,750")

    assert quote_problems(bad)
    assert quote_problems(good) == []


def test_facts_grader_finds_a_number_despite_separator_style():
    report = CountryReport(
        country=CountryCode.UK,
        status=ReportStatus.OK,
        incentives=[_record("Maximum discount of £3,750", "Band 1 is £3,750")],
    )
    comparison = Comparison(query="q", reports=[report], missing=[])
    tiny = GoldenCase(
        id="tiny",
        query="q",
        countries=(CountryCode.UK,),
        toolkit="fixture",
        expect_ok=(CountryCode.UK,),
        facts=(ExpectedFact(CountryCode.UK, ("3750", "3,750")),),
    )

    assert grade_facts(comparison, tiny).score == 1.0


def test_citations_grader_is_perfect_when_there_are_no_incentives():
    empty = Comparison(
        query="q",
        reports=[CountryReport(country=CountryCode.UK, status=ReportStatus.OK)],
        missing=[],
    )
    assert grade_citations(empty).score == 1.0


def test_gate_fails_when_quote_grounding_drops():
    bad = Comparison(
        query="q",
        reports=[
            CountryReport(
                country=CountryCode.UK,
                status=ReportStatus.OK,
                incentives=[_record("£9,999", "no amount here")],
            )
        ],
        missing=[],
    )
    result = EvalResult(case_id="bad", grades=grade_all(bad, FIXTURE_CASE), comparison=bad)
    report = gate([result], {**DEFAULT_THRESHOLDS, "facts": 0.0, "coverage": 0.0, "status": 0.0})

    assert report.ok is False
    assert any(failure.grader == "quote_grounding" for failure in report.failures)


def test_fixture_and_replay_goldens_pass_the_gate(settings):
    results = [run_case(FIXTURE_CASE, settings), run_case(REPLAY_CASE, settings)]
    report = gate(results)

    assert report.ok, report.summary()
