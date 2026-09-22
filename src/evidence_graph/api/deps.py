from fastapi import Request
from langgraph.graph.state import CompiledStateGraph

from evidence_graph.config import Settings


def get_graph(request: Request) -> CompiledStateGraph:
    return request.app.state.graph


def get_settings(request: Request) -> Settings:
    return request.app.state.settings
