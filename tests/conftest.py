import pytest
from fastapi.testclient import TestClient

from evidence_graph.api.main import create_app
from evidence_graph.config import Settings
from evidence_graph.graph import build_graph
from evidence_graph.tools.fixture import FixtureToolkit
from evidence_graph.use_cases.ev_incentives import DEFAULT_QUERY


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--live",
        action="store_true",
        default=False,
        help="run tests that call Tavily or other live services",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--live"):
        return
    skip_live = pytest.mark.skip(reason="live test; re-run with pytest --live")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)


@pytest.fixture
def settings() -> Settings:
    return Settings(_env_file=None, tool_mode="fixture", tavily_api_key=None)


@pytest.fixture
def query() -> str:
    return DEFAULT_QUERY


@pytest.fixture
def graph(settings: Settings):
    return build_graph(FixtureToolkit(), settings)


@pytest.fixture
def client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings=settings, toolkit=FixtureToolkit()))
