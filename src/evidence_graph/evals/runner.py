from dataclasses import dataclass
from uuid import uuid4

from evidence_graph.config import Settings
from evidence_graph.evals.goldens import CASES, GoldenCase
from evidence_graph.evals.graders import Grade, grade_all
from evidence_graph.graph import build_graph, run_comparison
from evidence_graph.state import Comparison
from evidence_graph.tools.fixture import FixtureToolkit
from evidence_graph.tools.recording import ReplayToolkit


@dataclass
class EvalResult:
    case_id: str
    grades: list[Grade]
    comparison: Comparison

    def as_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "grades": [
                {
                    "name": grade.name,
                    "score": grade.score,
                    "passed": grade.passed,
                    "total": grade.total,
                    "notes": grade.notes,
                }
                for grade in self.grades
            ],
        }


def toolkit_for(case: GoldenCase, settings: Settings):
    if case.toolkit == "replay":
        return ReplayToolkit(settings.recordings_dir)
    return FixtureToolkit()


def run_case(case: GoldenCase, settings: Settings) -> EvalResult:
    graph = build_graph(toolkit_for(case, settings), settings)
    comparison = run_comparison(
        graph,
        settings,
        case.query,
        list(case.countries),
        thread_id=f"eval-{case.id}-{uuid4().hex[:8]}",
        user_id="eval",
    )
    return EvalResult(case_id=case.id, grades=grade_all(comparison, case), comparison=comparison)


def run_cases(settings: Settings, cases: tuple[GoldenCase, ...] = CASES) -> list[EvalResult]:
    return [run_case(case, settings) for case in cases]
