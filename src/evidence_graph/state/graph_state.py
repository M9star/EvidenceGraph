import operator
from typing import Annotated, TypedDict

from evidence_graph.state.models import Comparison, CountryCode, CountryReport


class ResetReports(list):
    """Sentinel update: drop reports from an earlier run on this thread.

    `reports` still uses list-concat so four parallel researchers can append. A reused
    thread would otherwise keep growing. The planner sends this; researchers send lists.
    """


def reduce_reports(
    existing: list[CountryReport], incoming: list[CountryReport]
) -> list[CountryReport]:
    if type(incoming) is ResetReports:
        return []
    return [*existing, *incoming]


class ResearchState(TypedDict, total=False):
    query: str
    countries: list[CountryCode]
    reports: Annotated[list[CountryReport], reduce_reports]
    comparison: Comparison
    history: Annotated[list[Comparison], operator.add]


class ResearchTask(TypedDict):
    query: str
    country: CountryCode
