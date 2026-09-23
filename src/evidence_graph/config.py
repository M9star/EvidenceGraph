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
