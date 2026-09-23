from dataclasses import dataclass, field

from evidence_graph.graph.nodes.citations import check_record
from evidence_graph.state import CountryCode, IncentiveRecord
from evidence_graph.tools import FetchedPage, ResearchToolkit


@dataclass
class GateResult:
    accepted: list[IncentiveRecord] = field(default_factory=list)
    rejected: int = 0
    problems: list[str] = field(default_factory=list)

    @property
    def score(self) -> float:
        total = len(self.accepted) + self.rejected
        return len(self.accepted) / total if total else 0.0


def gate(records: list[IncentiveRecord], page: FetchedPage) -> GateResult:
    """Keep only records the citation checker fully supports; collect the rest as problems."""
    result = GateResult()
    for record in records:
        problems = check_record(record, page)
        if problems:
            result.rejected += 1
            result.problems.extend(problems)
        else:
            result.accepted.append(record)
    return result


def extract_with_gate(
    toolkit: ResearchToolkit, page: FetchedPage, country: CountryCode, max_attempts: int
) -> GateResult:
    """Extract, check, and retry once with the checker's feedback. Keep the best attempt."""
    best: GateResult | None = None
    feedback: str | None = None
    for _ in range(max_attempts):
        result = gate(toolkit.extract(page, country, feedback), page)
        if best is None or len(result.accepted) > len(best.accepted):
            best = result
        if not result.problems:
            break
        feedback = "\n".join(f"- {problem}" for problem in result.problems)
    assert best is not None
    return best
