from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, Field, HttpUrl, PlainSerializer

# Checkpoint serialization (msgpack) cannot encode pydantic Url objects, so dump as str.
SourceUrl = Annotated[HttpUrl, PlainSerializer(str, return_type=str)]


class CountryCode(StrEnum):
    FR = "FR"
    DE = "DE"
    UK = "UK"
    IN = "IN"


class ReportStatus(StrEnum):
    OK = "ok"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class Citation(BaseModel):
    url: SourceUrl
    title: str
    retrieved_at: datetime
    quote: str | None = None


class IncentiveRecord(BaseModel):
    name: str
    benefit: str
    eligibility: list[str]
    citations: list[Citation] = Field(min_length=1)


class CountryReport(BaseModel):
    country: CountryCode
    status: ReportStatus
    incentives: list[IncentiveRecord] = Field(default_factory=list)
    error: str | None = None
    warnings: list[str] = Field(default_factory=list)


class Comparison(BaseModel):
    query: str
    reports: list[CountryReport]
    missing: list[CountryCode]
