from typing import Annotated

from fastapi import Depends, HTTPException, Request
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph

from evidence_graph.auth import AuthError, Principal, QuotaStore, can_run, verify_bearer
from evidence_graph.config import Settings
from evidence_graph.memory import ThreadRecord, ThreadStore


def get_graph(request: Request) -> CompiledStateGraph:
    return request.app.state.graph


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_thread_store(request: Request) -> ThreadStore:
    return request.app.state.thread_store


def get_quota_store(request: Request) -> QuotaStore:
    return request.app.state.quota_store


def get_checkpointer(request: Request) -> BaseCheckpointSaver:
    return request.app.state.checkpointer


def get_principal(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> Principal:
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="missing bearer token")
    try:
        return verify_bearer(token.strip(), settings)
    except AuthError:
        raise HTTPException(status_code=401, detail="invalid token") from None


def require_researcher(
    principal: Annotated[Principal, Depends(get_principal)],
) -> Principal:
    if not can_run(principal):
        raise HTTPException(status_code=403, detail="researcher role required")
    return principal


def owned_thread(
    thread_id: str,
    principal: Principal,
    store: ThreadStore,
) -> ThreadRecord:
    # 404 for both missing and someone else's: a thread_id is not a capability.
    record = store.get(thread_id)
    if record is None or record.user_id != principal.user_id:
        raise HTTPException(status_code=404, detail="thread not found")
    return record
