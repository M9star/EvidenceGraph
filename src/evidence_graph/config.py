from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ToolMode = Literal["fixture", "replay", "live", "record"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EVIDENCEGRAPH_", env_file=".env", extra="ignore")

    tool_mode: ToolMode = "fixture"
    max_pages_per_country: int = Field(default=3, ge=1, le=10)
    recursion_limit: int = Field(default=12, ge=4, le=50)

    tavily_api_key: SecretStr | None = None
    search_max_results: int = Field(default=5, ge=1, le=20)

    fetch_timeout_s: float = Field(default=20.0, gt=0)
    fetch_max_bytes: int = Field(default=3_000_000, ge=10_000)
    page_max_chars: int = Field(default=40_000, ge=1_000)

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    ollama_num_ctx: int = Field(default=8192, ge=2048)
    model_timeout_s: float = Field(default=180.0, gt=0)

    extract_max_chars: int = Field(default=12_000, ge=1_000)
    extract_max_attempts: int = Field(default=2, ge=1, le=3)

    recordings_dir: Path = Path("tests/fixtures/recorded")

    # Auth. Tokens come from an IdP (or `python -m evidence_graph.auth` locally).
    jwt_secret: SecretStr | None = None
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    jwt_issuer: str | None = None
    jwt_audience: str | None = None
    daily_run_quota: int = Field(default=20, ge=1, le=1000)

    # When set, checkpoints, threads, and quotas persist in Postgres. Otherwise in-memory.
    database_url: str | None = None

    # Week 4 reliability. HTTP/model still have their own timeouts; these bound the graph.
    tool_timeout_s: float = Field(default=30.0, gt=0)
    country_timeout_s: float = Field(default=90.0, gt=0)
    run_timeout_s: float = Field(default=180.0, gt=0)
    max_tool_calls_per_researcher: int = Field(default=20, ge=1, le=100)
    tool_retries: int = Field(default=2, ge=0, le=5)
    retry_backoff_s: float = Field(default=0.05, ge=0)
    page_excerpt_chars: int = Field(default=12_000, ge=500)
    history_keep_recent: int = Field(default=2, ge=1, le=20)

    # Week 5 observability. Tracing is always on in-process. Exporters and LangSmith are opt-in.
    langsmith_api_key: SecretStr | None = None
    langsmith_project: str = "evidencegraph"
    otel_exporter: Literal["none", "console", "otlp"] = "none"
    otel_endpoint: str | None = None
    search_cost_usd: float = Field(default=0.008, ge=0)
    fetch_cost_usd: float = Field(default=0.0, ge=0)
    prompt_token_usd: float = Field(default=0.0, ge=0)
    completion_token_usd: float = Field(default=0.0, ge=0)
    eval_facts_min: float = Field(default=0.8, ge=0, le=1)
