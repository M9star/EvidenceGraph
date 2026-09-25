from datetime import UTC, datetime

from evidence_graph.evals.judge import heuristic_judge, llm_judge
from evidence_graph.state import Citation, IncentiveRecord


class FakeModel:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def generate_json(self, system, user, schema):
        return self.payload


def _record(benefit: str, quote: str) -> IncentiveRecord:
    return IncentiveRecord(
        name="Grant",
        benefit=benefit,
        eligibility=[],
        citations=[
            Citation(
                url="https://www.gov.uk/",
                title="t",
                retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
                quote=quote,
            )
        ],
    )


def test_heuristic_judge_flags_misattributed_amounts():
    ok, reason = heuristic_judge(_record("£3,750", "The seller includes a discount"))
    assert ok is False
    assert "3750" in reason


def test_llm_judge_reads_the_model_payload():
    model = FakeModel({"faithful": True, "reason": "quotes match"})
    ok, reason = llm_judge(model, _record("£3,750", "£3,750"), "The maximum discount is £3,750")
    assert ok is True
    assert reason == "quotes match"
