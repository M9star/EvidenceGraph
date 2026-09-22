from collections.abc import Callable, Mapping

from langgraph.types import Send

from evidence_graph.state import CountryCode, ResearchState
from evidence_graph.use_cases.ev_incentives import CountryProfile

RESEARCHER = "researcher"


def make_planner(
    profiles: Mapping[CountryCode, CountryProfile],
) -> Callable[[ResearchState], dict]:
    def plan(state: ResearchState) -> dict:
        requested = state.get("countries") or list(profiles)
        unknown = [code for code in requested if code not in profiles]
        if unknown:
            raise ValueError(f"unsupported countries: {unknown}")
        return {"countries": list(dict.fromkeys(requested))}

    return plan


def fan_out(state: ResearchState) -> list[Send]:
    return [
        Send(RESEARCHER, {"query": state["query"], "country": country})
        for country in state["countries"]
    ]
