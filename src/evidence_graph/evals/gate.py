from dataclasses import dataclass, field

from evidence_graph.config import Settings
from evidence_graph.evals.runner import EvalResult

DEFAULT_THRESHOLDS = {
    "coverage": 1.0,
    "status": 1.0,
    "citations": 1.0,
    "facts": 0.8,
    "quote_grounding": 1.0,
}


@dataclass
class GateFailure:
    case_id: str
    grader: str
    score: float
    minimum: float
    notes: list[str] = field(default_factory=list)


@dataclass
class GateReport:
    ok: bool
    failures: list[GateFailure]

    def summary(self) -> str:
        if self.ok:
            return "eval gate passed"
        lines = ["eval gate failed:"]
        for failure in self.failures:
            lines.append(
                f"  {failure.case_id}.{failure.grader}: {failure.score:.2f} < {failure.minimum:.2f}"
            )
            lines.extend(f"    - {note}" for note in failure.notes[:5])
        return "\n".join(lines)


def thresholds_from_settings(settings: Settings) -> dict[str, float]:
    values = dict(DEFAULT_THRESHOLDS)
    values["facts"] = settings.eval_facts_min
    return values


def gate(
    results: list[EvalResult],
    thresholds: dict[str, float] | None = None,
) -> GateReport:
    floors = thresholds or DEFAULT_THRESHOLDS
    failures: list[GateFailure] = []
    for result in results:
        for grade in result.grades:
            if grade.total == 0:
                continue
            minimum = floors.get(grade.name, 0.0)
            if grade.score + 1e-9 < minimum:
                failures.append(
                    GateFailure(
                        case_id=result.case_id,
                        grader=grade.name,
                        score=grade.score,
                        minimum=minimum,
                        notes=grade.notes,
                    )
                )
    return GateReport(ok=not failures, failures=failures)
