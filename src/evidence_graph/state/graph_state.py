import operator
from typing import Annotated, TypedDict

from evidence_graph.state.models import Comparison, CountryCode, CountryReport


class ResearchState(TypedDict, total=False):
    query: str
    countries: list[CountryCode]
    reports: Annotated[list[CountryReport], operator.add]
    comparison: Comparison


class ResearchTask(TypedDict):
    query: str
    country: CountryCode
