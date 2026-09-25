import time
from collections.abc import Mapping
from uuid import uuid4

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from evidence_graph.artifacts import ArtifactStore, InMemoryArtifactStore
from evidence_graph.config import Settings
from evidence_graph.graph.nodes.comparator import make_compare
from evidence_graph.graph.nodes.planner import RESEARCHER, fan_out, make_planner
from evidence_graph.graph.nodes.researcher import make_researcher
from evidence_graph.graph.policies import ReliabilityPolicy
from evidence_graph.memory.reports import InMemoryReportCache, ReportCache
from evidence_graph.obs.cost import CostLedger
from evidence_graph.obs.toolkit import TracedToolkit
from evidence_graph.obs.tracing import configure_tracing, span, traced_node
from evidence_graph.state import Comparison, CountryCode, ResearchState
from evidence_graph.tools import AllowlistedToolkit, ResearchToolkit
from evidence_graph.tools.artifacts import ArtifactToolkit
from evidence_graph.tools.registry import toolkit_for
from evidence_graph.tools.reliable import ReliableToolkit
from evidence_graph.use_cases.ev_incentives import EV_COUNTRIES, CountryProfile, allowlists


def build_graph(
    toolkit: ResearchToolkit,
    settings: Settings,
    profiles: Mapping[CountryCode, CountryProfile] = EV_COUNTRIES,
    checkpointer: BaseCheckpointSaver | None = None,
    policy: ReliabilityPolicy | None = None,
    report_cache: ReportCache | None = None,
    artifact_store: ArtifactStore | None = None,
    run_deadline: float | None = None,
    ledger: CostLedger | None = None,
) -> CompiledStateGraph:
    configure_tracing(settings)
    policy = policy or ReliabilityPolicy.from_settings(settings)
    report_cache = report_cache or InMemoryReportCache()
    store = artifact_store or InMemoryArtifactStore()
    ledger = ledger or CostLedger.from_settings(settings)
    guarded = AllowlistedToolkit(
        ArtifactToolkit(toolkit, store, policy.excerpt_chars),
        allowlists(profiles),
    )
    reliable = ReliableToolkit(TracedToolkit(guarded, ledger), policy, run_deadline=run_deadline)
    researcher = make_researcher(
        toolkit_for(RESEARCHER, reliable),
        profiles,
        settings.max_pages_per_country,
        settings.extract_max_attempts,
        report_cache=report_cache,
    )

    graph = StateGraph(ResearchState)
    graph.add_node("planner", traced_node("planner", make_planner(profiles)))
    graph.add_node(RESEARCHER, traced_node(RESEARCHER, researcher))
    compare = traced_node("comparator", make_compare(policy.history_keep_recent))
    graph.add_node("comparator", compare)

    graph.add_edge(START, "planner")
    graph.add_conditional_edges("planner", fan_out, [RESEARCHER])
    graph.add_edge(RESEARCHER, "comparator")
    graph.add_edge("comparator", END)

    compiled = graph.compile(checkpointer=checkpointer or MemorySaver())
    compiled.ledger = ledger  # type: ignore[attr-defined]
    return compiled


def invoke_comparison(
    graph: CompiledStateGraph,
    settings: Settings,
    query: str,
    countries: list[CountryCode],
    thread_id: str,
    *,
    user_id: str = "anonymous",
    run_id: str | None = None,
    request_id: str | None = None,
    ledger: CostLedger | None = None,
) -> tuple[Comparison, CostLedger]:
    configure_tracing(settings)
    deadline = time.monotonic() + settings.run_timeout_s
    run_id = run_id or str(uuid4())
    ledger = ledger or getattr(graph, "ledger", None) or CostLedger.from_settings(settings)
    ledger.start(user_id=user_id, thread_id=thread_id, run_id=run_id)
    started = time.monotonic()
    config = {
        "configurable": {
            "thread_id": thread_id,
            "user_id": user_id,
            "run_deadline": deadline,
            "run_id": run_id,
        },
        "metadata": {
            "user_id": user_id,
            "thread_id": thread_id,
            "run_id": run_id,
            "request_id": request_id,
        },
        "run_name": "comparison",
        "tags": ["evidencegraph"],
        "recursion_limit": settings.recursion_limit,
    }
    try:
        with span(
            "graph.run",
            **{
                "run.id": run_id,
                "user.id": user_id,
                "thread.id": thread_id,
                "request.id": request_id,
            },
        ):
            result = graph.invoke({"query": query, "countries": countries}, config)
    finally:
        ledger.finish(run_id, latency_s=time.monotonic() - started)
    return result["comparison"], ledger


def run_comparison(
    graph: CompiledStateGraph,
    settings: Settings,
    query: str,
    countries: list[CountryCode],
    thread_id: str,
    *,
    user_id: str = "anonymous",
    run_id: str | None = None,
    request_id: str | None = None,
    ledger: CostLedger | None = None,
) -> Comparison:
    comparison, _ledger = invoke_comparison(
        graph,
        settings,
        query,
        countries,
        thread_id,
        user_id=user_id,
        run_id=run_id,
        request_id=request_id,
        ledger=ledger,
    )
    return comparison
