from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, Field

from evidence_graph.api.deps import get_graph, get_settings
from evidence_graph.config import Settings
from evidence_graph.graph import run_comparison
from evidence_graph.state import Comparison, CountryCode
from evidence_graph.use_cases.ev_incentives import DEFAULT_QUERY, EV_COUNTRIES

router = APIRouter(tags=["comparisons"])


class ComparisonRequest(BaseModel):
    query: str = Field(default=DEFAULT_QUERY, min_length=10, max_length=500)
    countries: list[CountryCode] = Field(
        default_factory=lambda: list(EV_COUNTRIES), min_length=1, max_length=len(CountryCode)
    )


class ComparisonResponse(BaseModel):
    thread_id: str
    comparison: Comparison


@router.post("/comparisons", response_model=ComparisonResponse)
def create_comparison(
    body: ComparisonRequest,
    graph: Annotated[CompiledStateGraph, Depends(get_graph)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ComparisonResponse:
    thread_id = str(uuid4())
    comparison = run_comparison(graph, settings, body.query, body.countries, thread_id)
    return ComparisonResponse(thread_id=thread_id, comparison=comparison)
