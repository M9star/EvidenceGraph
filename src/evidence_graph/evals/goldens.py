from dataclasses import dataclass

from evidence_graph.state import CountryCode
from evidence_graph.use_cases.ev_incentives import DEFAULT_QUERY

ALL = (CountryCode.FR, CountryCode.DE, CountryCode.UK, CountryCode.IN)


@dataclass(frozen=True)
class ExpectedFact:
    """A fact that must appear somewhere in that country's report (name, benefit, rules, quotes)."""

    country: CountryCode
    needles: tuple[str, ...]


@dataclass(frozen=True)
class GoldenCase:
    id: str
    query: str
    countries: tuple[CountryCode, ...]
    toolkit: str
    expect_ok: tuple[CountryCode, ...]
    facts: tuple[ExpectedFact, ...] = ()


FIXTURE_CASE = GoldenCase(
    id="fixture-all-four",
    query=DEFAULT_QUERY,
    countries=ALL,
    toolkit="fixture",
    expect_ok=ALL,
    facts=tuple(ExpectedFact(code, ("Fixture benefit",)) for code in ALL),
)

REPLAY_CASE = GoldenCase(
    id="replay-recorded-live",
    query=DEFAULT_QUERY,
    countries=ALL,
    toolkit="replay",
    expect_ok=ALL,
    facts=(
        ExpectedFact(CountryCode.UK, ("3,750", "3750", "£3,750")),
        ExpectedFact(CountryCode.UK, ("1,500", "1500", "£1,500")),
        ExpectedFact(CountryCode.FR, ("47 000", "47,000", "47000")),
        ExpectedFact(CountryCode.FR, ("6 500", "6,500", "6500")),
        ExpectedFact(CountryCode.DE, ("80.000", "80,000", "80000")),
        ExpectedFact(CountryCode.IN, ("14,028", "14028")),
        ExpectedFact(CountryCode.IN, ("4,674", "4674")),
    ),
)

CASES = (FIXTURE_CASE, REPLAY_CASE)
