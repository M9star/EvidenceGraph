from fastapi import FastAPI

from evidence_graph import __version__
from evidence_graph.api.routes import compare, health
from evidence_graph.config import Settings
from evidence_graph.graph import build_graph
from evidence_graph.tools import ResearchToolkit
from evidence_graph.tools.factory import build_toolkit


def create_app(
    settings: Settings | None = None,
    toolkit: ResearchToolkit | None = None,
) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(title="EvidenceGraph", version=__version__)
    app.state.settings = settings
    app.state.graph = build_graph(toolkit or build_toolkit(settings), settings)
    app.include_router(health.router)
    app.include_router(compare.router, prefix="/v1")
    return app


app = create_app()
