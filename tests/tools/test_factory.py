from evidence_graph.config import Settings
from evidence_graph.tools.factory import build_search, build_toolkit
from evidence_graph.tools.fixture import FixtureToolkit
from evidence_graph.tools.live import LiveToolkit
from evidence_graph.tools.recording import RecordingToolkit, ReplayToolkit
from evidence_graph.tools.search import SeedSearch, TavilySearch


def settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_each_tool_mode_builds_the_matching_toolkit():
    assert isinstance(build_toolkit(settings(tool_mode="fixture")), FixtureToolkit)
    assert isinstance(build_toolkit(settings(tool_mode="replay")), ReplayToolkit)
    assert isinstance(build_toolkit(settings(tool_mode="live")), LiveToolkit)
    assert isinstance(build_toolkit(settings(tool_mode="record")), RecordingToolkit)


def test_search_falls_back_to_seed_urls_without_an_api_key():
    assert isinstance(build_search(settings(tavily_api_key=None)), SeedSearch)
    assert isinstance(build_search(settings(tavily_api_key="tvly-x")), TavilySearch)
