from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EVIDENCEGRAPH_", env_file=".env", extra="ignore")

    tool_mode: Literal["fixture"] = "fixture"
    max_pages_per_country: int = Field(default=3, ge=1, le=10)
    recursion_limit: int = Field(default=12, ge=4, le=50)
