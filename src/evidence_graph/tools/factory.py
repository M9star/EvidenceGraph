from collections.abc import Mapping

from evidence_graph.config import Settings
from evidence_graph.llm import OllamaModel
from evidence_graph.state.models import CountryCode
from evidence_graph.tools.base import ResearchToolkit, SearchProvider
from evidence_graph.tools.fixture import FixtureToolkit
from evidence_graph.tools.http_fetch import HttpFetcher
from evidence_graph.tools.live import LiveToolkit
from evidence_graph.tools.llm_extract import LlmExtractor
from evidence_graph.tools.recording import RecordingToolkit, ReplayToolkit
from evidence_graph.tools.search import SeedSearch, TavilySearch
from evidence_graph.use_cases.ev_incentives import (
    EV_COUNTRIES,
    CountryProfile,
    allowlists,
    seed_urls,
)


def build_search(
    settings: Settings, profiles: Mapping[CountryCode, CountryProfile] = EV_COUNTRIES
) -> SearchProvider:
    if settings.tavily_api_key is None:
        return SeedSearch(seed_urls(profiles))
    return TavilySearch(
        api_key=settings.tavily_api_key.get_secret_value(),
        allowlists=allowlists(profiles),
        max_results=settings.search_max_results,
        timeout_s=settings.fetch_timeout_s,
    )


def build_live_toolkit(
    settings: Settings, profiles: Mapping[CountryCode, CountryProfile] = EV_COUNTRIES
) -> LiveToolkit:
    fetcher = HttpFetcher(
        allowlists(profiles),
        timeout_s=settings.fetch_timeout_s,
        max_bytes=settings.fetch_max_bytes,
        max_chars=settings.page_max_chars,
    )
    model = OllamaModel(
        settings.ollama_base_url,
        settings.ollama_model,
        num_ctx=settings.ollama_num_ctx,
        timeout_s=settings.model_timeout_s,
    )
    extractor = LlmExtractor(model, max_chars=settings.extract_max_chars)
    return LiveToolkit(build_search(settings, profiles), fetcher, extractor)


def build_toolkit(
    settings: Settings, profiles: Mapping[CountryCode, CountryProfile] = EV_COUNTRIES
) -> ResearchToolkit:
    match settings.tool_mode:
        case "fixture":
            return FixtureToolkit()
        case "replay":
            return ReplayToolkit(settings.recordings_dir)
        case "live":
            return build_live_toolkit(settings, profiles)
        case "record":
            return RecordingToolkit(build_live_toolkit(settings, profiles), settings.recordings_dir)
