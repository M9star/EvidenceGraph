from dataclasses import dataclass, field

from evidence_graph.evals.goldens import ExpectedFact, GoldenCase
from evidence_graph.graph.nodes.citations import claim_numbers, normalize, number_in_text
from evidence_graph.state import Comparison, CountryReport, IncentiveRecord, ReportStatus


@dataclass
class Grade:
    name: str
    score: float
    passed: int
    total: int
    notes: list[str] = field(default_factory=list)


def _report_text(report: CountryReport) -> str:
    parts: list[str] = []
    for incentive in report.incentives:
        parts.extend([incentive.name, incentive.benefit, *incentive.eligibility])
        parts.extend(citation.quote or "" for citation in incentive.citations)
    return normalize(" ".join(parts))


def _fact_hits(report: CountryReport, fact: ExpectedFact) -> bool:
    text = _report_text(report)
    raw = " ".join(
        part
        for incentive in report.incentives
        for part in (
            incentive.name,
            incentive.benefit,
            *incentive.eligibility,
            *(citation.quote or "" for citation in incentive.citations),
        )
    )
    for needle in fact.needles:
        if normalize(needle) in text:
            return True
        digits = "".join(ch for ch in needle if ch.isdigit())
        if digits and number_in_text(digits, raw):
            return True
    return False


def grade_coverage(comparison: Comparison, case: GoldenCase) -> Grade:
    have = {report.country for report in comparison.reports}
    found = [code for code in case.countries if code in have]
    missing = [code.value for code in case.countries if code not in have]
    return Grade(
        "coverage",
        len(found) / len(case.countries) if case.countries else 1.0,
        len(found),
        len(case.countries),
        [f"missing {code}" for code in missing],
    )


def grade_status(comparison: Comparison, case: GoldenCase) -> Grade:
    by_country = {report.country: report for report in comparison.reports}
    ok = [
        code
        for code in case.expect_ok
        if code in by_country and by_country[code].status is ReportStatus.OK
    ]
    notes = [
        f"{code.value} is {by_country[code].status.value}"
        if code in by_country
        else f"{code.value} missing"
        for code in case.expect_ok
        if code not in by_country or by_country[code].status is not ReportStatus.OK
    ]
    return Grade(
        "status",
        len(ok) / len(case.expect_ok) if case.expect_ok else 1.0,
        len(ok),
        len(case.expect_ok),
        notes,
    )


def grade_citations(comparison: Comparison) -> Grade:
    incentives = [item for report in comparison.reports for item in report.incentives]
    cited = [item for item in incentives if item.citations]
    notes = [item.name for item in incentives if not item.citations]
    return Grade(
        "citations",
        len(cited) / len(incentives) if incentives else 1.0,
        len(cited),
        len(incentives),
        notes,
    )


def grade_facts(comparison: Comparison, case: GoldenCase) -> Grade:
    if not case.facts:
        return Grade("facts", 1.0, 0, 0)
    by_country = {report.country: report for report in comparison.reports}
    hits: list[ExpectedFact] = []
    notes: list[str] = []
    for fact in case.facts:
        report = by_country.get(fact.country)
        if report is not None and _fact_hits(report, fact):
            hits.append(fact)
        else:
            notes.append(f"{fact.country.value}: none of {fact.needles}")
    return Grade("facts", len(hits) / len(case.facts), len(hits), len(case.facts), notes)


def quote_problems(record: IncentiveRecord) -> list[str]:
    """Deterministic faithfulness: benefit amounts must sit in the record's own quotes."""
    quotes = [citation.quote for citation in record.citations if citation.quote]
    if not quotes:
        return [f"{record.name!r}: no verbatim quote"]
    quoted = " ".join(quotes)
    return [
        f"{record.name!r}: benefit number {digits} is not in its quotes"
        for digits in claim_numbers(record.benefit)
        if not number_in_text(digits, quoted)
    ]


def grade_quote_grounding(comparison: Comparison) -> Grade:
    incentives = [item for report in comparison.reports for item in report.incentives]
    problems = [problem for item in incentives for problem in quote_problems(item)]
    clean = sum(1 for item in incentives if not quote_problems(item))
    return Grade(
        "quote_grounding",
        clean / len(incentives) if incentives else 1.0,
        clean,
        len(incentives),
        problems,
    )


def grade_all(comparison: Comparison, case: GoldenCase) -> list[Grade]:
    return [
        grade_coverage(comparison, case),
        grade_status(comparison, case),
        grade_citations(comparison),
        grade_facts(comparison, case),
        grade_quote_grounding(comparison),
    ]
