from datetime import UTC, datetime

import pytest

from evidence_graph.graph.nodes.citations import check_record
from evidence_graph.state import Citation, IncentiveRecord
from evidence_graph.tools import FetchedPage

# Modelled on the real PM E-DRIVE page, where amounts for different vehicles sit side by side.
PAGE = FetchedPage(
    url="https://pmedrive.heavyindustries.gov.in/",
    title="PM E-DRIVE",
    text=(
        "e-Ambulances\nThe Demand Incentive will be lower of:\n"
        "₹ 30,000 multiplied by the battery capacity in kilowatt-hour (kWh)\n"
        "35% of the ex-factory price of the vehicle.\n"
        "e-Trucks\nDemand incentive will be the lowest of:\n"
        "a) ₹5,000 × battery capacity in kWh\n"
        "Le coût doit être inférieur ou égal à 47 000 € TTC."
    ),
    retrieved_at=datetime(2026, 9, 23, tzinfo=UTC),
)


def record(benefit: str, quotes: list[str | None], eligibility=(), url: str = PAGE.url):
    return IncentiveRecord(
        name="Test incentive",
        benefit=benefit,
        eligibility=list(eligibility),
        citations=[
            Citation(url=url, title="t", retrieved_at=PAGE.retrieved_at, quote=q) for q in quotes
        ],
    )


def test_supported_record_passes():
    ok = record(
        "₹30,000 per kWh or 35% of ex-factory price",
        ["₹ 30,000 multiplied by the battery capacity", "35% of the ex-factory price"],
    )

    assert check_record(ok, PAGE) == []


def test_quotes_match_despite_whitespace_and_case_differences():
    ok = record("Incentive", ["THE DEMAND INCENTIVE   will be\nlower of:"])

    assert check_record(ok, PAGE) == []


@pytest.mark.parametrize(
    ("bad", "reason"),
    [
        (record("Incentive", [None]), "no verbatim quote"),
        (record("Incentive", ["The grant is £9,999."]), "quote not found"),
        (record("Up to ₹8,000", ["₹5,000 × battery capacity in kWh"]), "8000"),
        (record("Incentive", ["35% of the ex-factory"], eligibility=["Max 12 tonnes"]), "12"),
        (record("Incentive", ["35%"], url="https://pib.gov.in/other"), "other than the fetched"),
    ],
)
def test_unsupported_records_are_rejected_with_a_reason(bad, reason):
    problems = check_record(bad, PAGE)

    assert problems
    assert any(reason in problem for problem in problems)


def test_benefit_amount_must_be_in_its_own_quotes_not_just_somewhere_on_the_page():
    # The real failure: the e-truck amount attributed to e-2Ws, quoting unrelated text.
    misattributed = record("₹5,000 per kWh", ["The Demand Incentive will be lower of:"])

    problems = check_record(misattributed, PAGE)

    assert any("benefit number 5000 is not in its quotes" in p for p in problems)


def test_numbers_match_across_separator_styles():
    french = record("Price cap of €47,000", ["inférieur ou égal à 47 000 € TTC"])

    assert check_record(french, PAGE) == []
