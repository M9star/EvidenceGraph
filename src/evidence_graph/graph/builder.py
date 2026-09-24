import time
from collections.abc import Mapping

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
) -> CompiledStateGraph:
    policy = policy or ReliabilityPolicy.from_settings(settings)
    report_cache = report_cache or InMemoryReportCache()
    store = artifact_store or InMemoryArtifactStore()
    guarded = AllowlistedToolkit(
        ArtifactToolkit(toolkit, store, policy.excerpt_chars),
        allowlists(profiles),
    )
    reliable = ReliableToolkit(guarded, policy, run_deadline=run_deadline)
    researcher = make_researcher(
        toolkit_for(RESEARCHER, reliable),
        profiles,
        settings.max_pages_per_country,
        settings.extract_max_attempts,
        report_cache=report_cache,
    )

    graph = StateGraph(ResearchState)
    graph.add_node("planner", make_planner(profiles))
    graph.add_node(RESEARCHER, researcher)
    graph.add_node("comparator", make_compare(policy.history_keep_recent))

    graph.add_edge(START, "planner")
    graph.add_conditional_edges("planner", fan_out, [RESEARCHER])
    graph.add_edge(RESEARCHER, "comparator")
    graph.add_edge("comparator", END)

    return graph.compile(checkpointer=checkpointer or MemorySaver())


def run_comparison(
    graph: CompiledStateGraph,
    settings: Settings,
    query: str,
    countries: list[CountryCode],
    thread_id: str,
    *,
    user_id: str = "anonymous",
) -> Comparison:
    deadline = time.monotonic() + settings.run_timeout_s
    config = {
        "configurable": {
            "thread_id": thread_id,
            "user_id": user_id,
            "run_deadline": deadline,
        },
        "metadata": {"user_id": user_id},
        "recursion_limit": settings.recursion_limit,
    }
    result = graph.invoke({"query": query, "countries": countries}, config)
    return result["comparison"]
