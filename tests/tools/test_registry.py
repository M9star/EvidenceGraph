import pytest

from evidence_graph.state import CountryCode
from evidence_graph.tools import ToolPolicyError
from evidence_graph.tools.fixture import FixtureToolkit
from evidence_graph.tools.registry import NODE_TOOLS, ToolName, toolkit_for


def test_only_the_researcher_is_granted_tools():
    granted = {node for node, tools in NODE_TOOLS.items() if tools}

    assert granted == {"researcher"}
    assert NODE_TOOLS["researcher"] == frozenset(ToolName)


@pytest.mark.parametrize("node", ["planner", "comparator", "citation_checker", "quality_gate"])
def test_nodes_without_grants_cannot_search_the_web(node):
    scoped = toolkit_for(node, FixtureToolkit())

    with pytest.raises(ToolPolicyError, match=node):
        scoped.search("ev grants", CountryCode.UK)


def test_researcher_can_use_its_granted_tools():
    scoped = toolkit_for("researcher", FixtureToolkit())

    hits = scoped.search("ev grants", CountryCode.UK)
    page = scoped.fetch(hits[0].url, CountryCode.UK)

    assert scoped.extract(page, CountryCode.UK)


def test_unregistered_nodes_get_nothing():
    with pytest.raises(ToolPolicyError, match="no tool grant"):
        toolkit_for("rogue_agent", FixtureToolkit())
