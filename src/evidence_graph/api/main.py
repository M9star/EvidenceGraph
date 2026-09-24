from fastapi import FastAPI
from langgraph.checkpoint.base import BaseCheckpointSaver

from evidence_graph import __version__
from evidence_graph.api.routes import compare, health, threads
from evidence_graph.auth import QuotaStore
from evidence_graph.config import Settings
from evidence_graph.graph import build_graph
from evidence_graph.memory import ThreadStore, build_stores
from evidence_graph.tools import ResearchToolkit
from evidence_graph.tools.factory import build_toolkit


def create_app(
    settings: Settings | None = None,
    toolkit: ResearchToolkit | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
    thread_store: ThreadStore | None = None,
    quota_store: QuotaStore | None = None,
) -> FastAPI:
    settings = settings or Settings()
    if checkpointer is None or thread_store is None or quota_store is None:
        built_checkpointer, built_threads, built_quotas = build_stores(settings)
        checkpointer = checkpointer or built_checkpointer
        thread_store = thread_store or built_threads
        quota_store = quota_store or built_quotas
    app = FastAPI(title="EvidenceGraph", version=__version__)
    app.state.settings = settings
    app.state.graph = build_graph(
        toolkit or build_toolkit(settings), settings, checkpointer=checkpointer
    )
    app.state.checkpointer = checkpointer
    app.state.thread_store = thread_store
    app.state.quota_store = quota_store
    app.include_router(health.router)
    app.include_router(compare.router, prefix="/v1")
    app.include_router(threads.router, prefix="/v1")
    return app


app = create_app()
