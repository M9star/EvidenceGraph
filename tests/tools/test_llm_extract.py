from datetime import UTC, datetime

import pytest

from evidence_graph.llm import ModelError
from evidence_graph.state import CountryCode
from evidence_graph.tools import FetchedPage, ToolUnavailableError
from evidence_graph.tools.llm_extract import EXTRACTION_SCHEMA, LlmExtractor

PAGE = FetchedPage(
    url="https://www.gov.uk/grant",
    title="Electric Car Grant",
    text="The maximum discount available for cars assessed as Band 1 is £3,750.",
    retrieved_at=datetime(2026, 9, 23, tzinfo=UTC),
)


class FakeModel:
    def __init__(self, response=None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[dict] = []

    def generate_json(self, system, user, schema):
        self.calls.append({"system": system, "user": user, "schema": schema})
        if self.error:
            raise self.error
        return self.response


def test_records_are_cited_with_the_quotes_the_model_returned():
    model = FakeModel(
        {
            "incentives": [
                {
                    "name": "Band 1",
                    "benefit": "Up to £3,750",
                    "eligibility": ["Band 1 car"],
                    "quotes": ["Band 1 is £3,750."],
                },
                {"name": "", "benefit": "malformed"},
            ]
        }
    )

    records = LlmExtractor(model).extract(PAGE, CountryCode.UK)

    assert len(records) == 1
    citation = records[0].citations[0]
    assert str(citation.url) == PAGE.url
    assert citation.quote == "Band 1 is £3,750."
    assert model.calls[0]["schema"] is EXTRACTION_SCHEMA


def test_schema_requires_quotes_so_constrained_models_must_provide_evidence():
    item = EXTRACTION_SCHEMA["$defs"]["_ExtractedIncentive"]

    assert "quotes" in item["required"]
    assert item["properties"]["quotes"]["minItems"] == 1


def test_feedback_is_sent_back_to_the_model_on_retry():
    model = FakeModel({"incentives": []})

    LlmExtractor(model).extract(PAGE, CountryCode.UK, feedback="- number 9999 not in page")

    assert "number 9999 not in page" in model.calls[0]["user"]


def test_page_text_sent_to_the_model_is_capped():
    model = FakeModel({"incentives": []})
    long_page = PAGE.model_copy(update={"text": "x" * 5_000})

    LlmExtractor(model, max_chars=1_000).extract(long_page, CountryCode.UK)

    assert "x" * 1_000 in model.calls[0]["user"]
    assert "x" * 1_001 not in model.calls[0]["user"]


def test_model_errors_become_tool_unavailable():
    model = FakeModel(error=ModelError("ollama down"))

    with pytest.raises(ToolUnavailableError, match="ollama down"):
        LlmExtractor(model).extract(PAGE, CountryCode.UK)
