import operator
from typing import Annotated, TypedDict

from evidence_graph.state.models import Comparison, CountryCode, CountryReport


class ResetReports(list):
    """Sentinel update: drop reports from an earlier run on this thread.

    `reports` still uses list-concat so four parallel researchers can append. A reused
    thread would otherwise keep growing. The planner sends this; researchers send lists.
    """


class ResetHistory(list):
    """Replace `history` with the items in this list (the recent turns we keep raw)."""


def reduce_reports(
    existing: list[CountryReport], incoming: list[CountryReport]
) -> list[CountryReport]:
    if type(incoming) is ResetReports:
        return []
    return [*existing, *incoming]


def reduce_history(existing: list[Comparison], incoming: list[Comparison]) -> list[Comparison]:
    if type(incoming) is ResetHistory:
        return list(incoming)
    return [*existing, *incoming]


class ResearchState(TypedDict, total=False):
    query: str
    countries: list[CountryCode]
    reports: Annotated[list[CountryReport], reduce_reports]
    comparison: Comparison
    history: Annotated[list[Comparison], reduce_history]
    history_summaries: Annotated[list[str], operator.add]


class ResearchTask(TypedDict):
    query: str
    country: CountryCode
