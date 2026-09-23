from typing import Any

from pydantic import BaseModel, Field, ValidationError

from evidence_graph.llm.base import ModelError, StructuredModel
from evidence_graph.state.models import Citation, CountryCode, IncentiveRecord
from evidence_graph.tools.base import FetchedPage, ToolUnavailableError

SYSTEM_PROMPT = """\
You extract electric-vehicle incentives from ONE official government web page.

Rules:
- Use only the page text you are given. Never use outside knowledge.
- Write name, benefit, and eligibility in English.
- quotes: copy 1 to 3 short passages from the page EXACTLY as written, in the page's own
  language, character for character. Each quote must support the benefit or eligibility.
- Every number you write (amounts, prices, dates, limits) must appear in the page text.
- If the page describes no incentive, return {"incentives": []}.
"""


class _ExtractedIncentive(BaseModel):
    name: str = Field(min_length=1)
    benefit: str = Field(min_length=1)
    eligibility: list[str]
    quotes: list[str] = Field(min_length=1, max_length=3)


class _Extraction(BaseModel):
    incentives: list[_ExtractedIncentive] = Field(default_factory=list)


EXTRACTION_SCHEMA: dict[str, Any] = _Extraction.model_json_schema()


class LlmExtractor:
    """Turns one fetched page into cited IncentiveRecords using any StructuredModel."""

    def __init__(self, model: StructuredModel, max_chars: int = 12_000) -> None:
        self._model = model
        self._max_chars = max_chars

    def extract(
        self, page: FetchedPage, country: CountryCode, feedback: str | None = None
    ) -> list[IncentiveRecord]:
        prompt = self._prompt(page, country, feedback)
        try:
            raw = self._model.generate_json(SYSTEM_PROMPT, prompt, EXTRACTION_SCHEMA)
        except ModelError as exc:
            raise ToolUnavailableError(f"extract {page.url}: {exc}") from exc

        items = raw.get("incentives")
        records: list[IncentiveRecord] = []
        for item in items if isinstance(items, list) else []:
            try:
                parsed = _ExtractedIncentive.model_validate(item)
            except ValidationError:
                continue
            records.append(self._to_record(parsed, page))
        return records

    def _prompt(self, page: FetchedPage, country: CountryCode, feedback: str | None) -> str:
        parts = [
            f"Country: {country}",
            f"Page URL: {page.url}",
            f"Page title: {page.title}",
            "Page text:",
            "<<<",
            page.text[: self._max_chars],
            ">>>",
        ]
        if feedback:
            parts += [
                "Your previous answer was rejected for these reasons. Fix them, and drop any "
                "incentive you cannot support with an exact quote:",
                feedback,
            ]
        return "\n".join(parts)

    @staticmethod
    def _to_record(item: _ExtractedIncentive, page: FetchedPage) -> IncentiveRecord:
        quotes = [q.strip() for q in item.quotes if q.strip()] or [None]
        return IncentiveRecord(
            name=item.name.strip(),
            benefit=item.benefit.strip(),
            eligibility=[rule.strip() for rule in item.eligibility if rule.strip()],
            citations=[
                Citation(url=page.url, title=page.title, retrieved_at=page.retrieved_at, quote=q)
                for q in quotes
            ],
        )
