from typing import Any

from evidence_graph.evals.graders import quote_problems
from evidence_graph.llm.base import ModelError, StructuredModel
from evidence_graph.state import IncentiveRecord

JUDGE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "faithful": {"type": "boolean"},
        "reason": {"type": "string"},
    },
    "required": ["faithful"],
}


def heuristic_judge(record: IncentiveRecord) -> tuple[bool, str]:
    """Offline judge: every benefit number must appear in the record's own quotes."""
    problems = quote_problems(record)
    if problems:
        return False, "; ".join(problems)
    return True, "quotes support the benefit numbers"


def llm_judge(model: StructuredModel, record: IncentiveRecord, page_text: str) -> tuple[bool, str]:
    """Optional model judge. Use only when a page is in hand; not required for CI."""
    prompt = (
        f"Incentive name: {record.name}\n"
        f"Claimed benefit: {record.benefit}\n"
        f"Eligibility: {'; '.join(record.eligibility)}\n"
        f"Quotes: {[c.quote for c in record.citations if c.quote]}\n"
        "Page text:\n<<<\n"
        f"{page_text[:8000]}\n"
        ">>>\n"
        "Is every claimed number and eligibility rule supported by the quotes or the page? "
        "Return faithful=false if the benefit looks borrowed from a different scheme on the page."
    )
    try:
        raw = model.generate_json(
            "You judge whether an extracted incentive is faithful to one official page.",
            prompt,
            JUDGE_SCHEMA,
        )
    except ModelError as exc:
        return False, f"judge failed: {exc}"
    return bool(raw.get("faithful")), str(raw.get("reason") or "")
