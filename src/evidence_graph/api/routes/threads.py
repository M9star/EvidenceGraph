from typing import Annotated

from fastapi import APIRouter, Depends
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel

from evidence_graph.api.deps import (
    get_checkpointer,
    get_graph,
    get_principal,
    get_thread_store,
    owned_thread,
)
from evidence_graph.auth import Principal
from evidence_graph.memory import ThreadRecord, ThreadStore, delete_thread_checkpoints
from evidence_graph.state import Comparison

router = APIRouter(tags=["threads"])


class ThreadSummary(BaseModel):
    thread_id: str
    query: str
    created_at: str
    updated_at: str


class ThreadDetail(ThreadSummary):
    comparison: Comparison | None
    history: list[Comparison]
    history_summaries: list[str]


@router.get("/threads", response_model=list[ThreadSummary])
def list_threads(
    principal: Annotated[Principal, Depends(get_principal)],
    threads: Annotated[ThreadStore, Depends(get_thread_store)],
) -> list[ThreadSummary]:
    return [_summary(record) for record in threads.list_for_user(principal.user_id)]


@router.get("/threads/{thread_id}", response_model=ThreadDetail)
def get_thread(
    thread_id: str,
    principal: Annotated[Principal, Depends(get_principal)],
    threads: Annotated[ThreadStore, Depends(get_thread_store)],
    graph: Annotated[CompiledStateGraph, Depends(get_graph)],
) -> ThreadDetail:
    record = owned_thread(thread_id, principal, threads)
    snapshot = graph.get_state({"configurable": {"thread_id": thread_id}})
    values = snapshot.values if snapshot else {}
    return ThreadDetail(
        **_summary(record).model_dump(),
        comparison=_as_comparison(values.get("comparison")),
        history=[c for item in values.get("history", []) if (c := _as_comparison(item))],
        history_summaries=[str(item) for item in values.get("history_summaries", [])],
    )


@router.delete("/threads/{thread_id}", status_code=204)
def delete_thread(
    thread_id: str,
    principal: Annotated[Principal, Depends(get_principal)],
    threads: Annotated[ThreadStore, Depends(get_thread_store)],
    checkpointer: Annotated[BaseCheckpointSaver, Depends(get_checkpointer)],
) -> None:
    owned_thread(thread_id, principal, threads)
    threads.delete(thread_id)
    delete_thread_checkpoints(checkpointer, thread_id)


def _summary(record: ThreadRecord) -> ThreadSummary:
    return ThreadSummary(
        thread_id=record.thread_id,
        query=record.query,
        created_at=record.created_at.isoformat(),
        updated_at=record.updated_at.isoformat(),
    )


def _as_comparison(value: object) -> Comparison | None:
    if value is None:
        return None
    if isinstance(value, Comparison):
        return value
    if isinstance(value, dict):
        return Comparison.model_validate(value)
    return None
