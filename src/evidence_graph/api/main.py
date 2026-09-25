from uuid import uuid4

from fastapi import FastAPI
from langgraph.checkpoint.base import BaseCheckpointSaver
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from evidence_graph import __version__
from evidence_graph.api.routes import compare, health, threads
from evidence_graph.auth import QuotaStore
from evidence_graph.config import Settings
from evidence_graph.graph import build_graph
from evidence_graph.memory import ThreadStore, build_stores
from evidence_graph.obs.cost import CostLedger
from evidence_graph.obs.langsmith import configure_langsmith
from evidence_graph.obs.tracing import configure_tracing, span
from evidence_graph.tools import ResearchToolkit
from evidence_graph.tools.factory import build_toolkit


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid4())
        request.state.request_id = request_id
        with span(
            "http.request",
            **{
                "http.method": request.method,
                "http.route": request.url.path,
                "request.id": request_id,
            },
        ):
            response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response


def create_app(
    settings: Settings | None = None,
    toolkit: ResearchToolkit | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
    thread_store: ThreadStore | None = None,
    quota_store: QuotaStore | None = None,
    ledger: CostLedger | None = None,
) -> FastAPI:
    settings = settings or Settings()
    configure_tracing(settings)
    configure_langsmith(settings)
    if checkpointer is None or thread_store is None or quota_store is None:
        built_checkpointer, built_threads, built_quotas = build_stores(settings)
        checkpointer = checkpointer or built_checkpointer
        thread_store = thread_store or built_threads
        quota_store = quota_store or built_quotas
    ledger = ledger or CostLedger.from_settings(settings)
    app = FastAPI(title="EvidenceGraph", version=__version__)
    app.add_middleware(RequestIdMiddleware)
    app.state.settings = settings
    app.state.ledger = ledger
    app.state.graph = build_graph(
        toolkit or build_toolkit(settings),
        settings,
        checkpointer=checkpointer,
        ledger=ledger,
    )
    app.state.checkpointer = checkpointer
    app.state.thread_store = thread_store
    app.state.quota_store = quota_store
    app.include_router(health.router)
    app.include_router(compare.router, prefix="/v1")
    app.include_router(threads.router, prefix="/v1")
    return app


app = create_app()
