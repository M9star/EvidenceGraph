from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, Field

from evidence_graph.api.deps import (
    get_graph,
    get_quota_store,
    get_settings,
    get_thread_store,
    owned_thread,
    require_researcher,
)
from evidence_graph.auth import Principal, QuotaExceeded, QuotaStore
from evidence_graph.config import Settings
from evidence_graph.graph import run_comparison
from evidence_graph.memory import ThreadStore
from evidence_graph.state import Comparison, CountryCode
from evidence_graph.use_cases.ev_incentives import DEFAULT_QUERY, EV_COUNTRIES

router = APIRouter(tags=["comparisons"])


class ComparisonRequest(BaseModel):
    query: str = Field(default=DEFAULT_QUERY, min_length=10, max_length=500)
    countries: list[CountryCode] = Field(
        default_factory=lambda: list(EV_COUNTRIES), min_length=1, max_length=len(CountryCode)
    )
    thread_id: str | None = Field(default=None, min_length=1, max_length=128)


class ComparisonResponse(BaseModel):
    thread_id: str
    comparison: Comparison


@router.post("/comparisons", response_model=ComparisonResponse)
def create_comparison(
    body: ComparisonRequest,
    graph: Annotated[CompiledStateGraph, Depends(get_graph)],
    settings: Annotated[Settings, Depends(get_settings)],
    principal: Annotated[Principal, Depends(require_researcher)],
    threads: Annotated[ThreadStore, Depends(get_thread_store)],
    quotas: Annotated[QuotaStore, Depends(get_quota_store)],
) -> ComparisonResponse:
    if body.thread_id is None:
        thread_id = str(uuid4())
        threads.create(principal.user_id, thread_id, body.query)
    else:
        owned_thread(body.thread_id, principal, threads)
        threads.touch(body.thread_id, body.query)
        thread_id = body.thread_id

    try:
        quotas.consume(principal.user_id, settings.daily_run_quota)
    except QuotaExceeded as exc:
        raise HTTPException(
            status_code=429,
            detail="daily run quota exceeded",
            headers={"Retry-After": "86400"},
        ) from exc

    comparison = run_comparison(
        graph,
        settings,
        body.query,
        body.countries,
        thread_id,
        user_id=principal.user_id,
    )
    return ComparisonResponse(thread_id=thread_id, comparison=comparison)
