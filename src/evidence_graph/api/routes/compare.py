from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, Field

from evidence_graph.api.deps import (
    get_graph,
    get_ledger,
    get_quota_store,
    get_request_id,
    get_settings,
    get_thread_store,
    owned_thread,
    require_researcher,
)
from evidence_graph.auth import Principal, QuotaExceeded, QuotaStore
from evidence_graph.config import Settings
from evidence_graph.graph import invoke_comparison
from evidence_graph.memory import ThreadStore
from evidence_graph.obs.cost import CostLedger
from evidence_graph.state import Comparison, CountryCode
from evidence_graph.use_cases.ev_incentives import DEFAULT_QUERY, EV_COUNTRIES

router = APIRouter(tags=["comparisons"])


class ComparisonRequest(BaseModel):
    query: str = Field(default=DEFAULT_QUERY, min_length=10, max_length=500)
    countries: list[CountryCode] = Field(
        default_factory=lambda: list(EV_COUNTRIES), min_length=1, max_length=len(CountryCode)
    )
    thread_id: str | None = Field(default=None, min_length=1, max_length=128)


class RunSummary(BaseModel):
    run_id: str
    latency_s: float
    tool_calls: int
    tokens: int
    estimated_usd: float


class ComparisonResponse(BaseModel):
    thread_id: str
    comparison: Comparison
    run: RunSummary


@router.post("/comparisons", response_model=ComparisonResponse)
def create_comparison(
    body: ComparisonRequest,
    graph: Annotated[CompiledStateGraph, Depends(get_graph)],
    settings: Annotated[Settings, Depends(get_settings)],
    principal: Annotated[Principal, Depends(require_researcher)],
    threads: Annotated[ThreadStore, Depends(get_thread_store)],
    quotas: Annotated[QuotaStore, Depends(get_quota_store)],
    ledger: Annotated[CostLedger, Depends(get_ledger)],
    request_id: Annotated[str | None, Depends(get_request_id)],
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

    run_id = str(uuid4())
    comparison, used = invoke_comparison(
        graph,
        settings,
        body.query,
        body.countries,
        thread_id,
        user_id=principal.user_id,
        run_id=run_id,
        request_id=request_id,
        ledger=ledger,
    )
    cost = used.get(run_id)
    summary = (
        cost.summary(used.rates)
        if cost is not None
        else {
            "run_id": run_id,
            "latency_s": 0.0,
            "tool_calls": 0,
            "tokens": 0,
            "estimated_usd": 0.0,
        }
    )
    return ComparisonResponse(thread_id=thread_id, comparison=comparison, run=RunSummary(**summary))
