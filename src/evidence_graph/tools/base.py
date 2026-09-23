from datetime import datetime
from typing import Protocol

from pydantic import BaseModel

from evidence_graph.state.models import CountryCode, IncentiveRecord


class ToolError(Exception):
    pass


class ToolPolicyError(ToolError):
    pass


class ToolUnavailableError(ToolError):
    pass


class SearchHit(BaseModel):
    url: str
    title: str


class FetchedPage(BaseModel):
    url: str
    title: str
    text: str
    retrieved_at: datetime


class ResearchToolkit(Protocol):
    def search(self, query: str, country: CountryCode) -> list[SearchHit]: ...

    def fetch(self, url: str, country: CountryCode) -> FetchedPage: ...

    def extract(
        self, page: FetchedPage, country: CountryCode, feedback: str | None = None
    ) -> list[IncentiveRecord]: ...


class SearchProvider(Protocol):
    def search(self, query: str, country: CountryCode) -> list[SearchHit]: ...
