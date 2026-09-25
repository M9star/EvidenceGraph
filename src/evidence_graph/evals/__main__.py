"""Run golden evals and exit 1 if a score falls below the CI gate.

uv run python -m evidence_graph.evals
"""

import json
import sys

from evidence_graph.config import Settings
from evidence_graph.evals.gate import gate, thresholds_from_settings
from evidence_graph.evals.runner import run_cases


def main(argv: list[str] | None = None) -> int:
    del argv
    settings = Settings()
    results = run_cases(settings)
    report = gate(results, thresholds_from_settings(settings))
    payload = {
        "ok": report.ok,
        "results": [result.as_dict() for result in results],
        "failures": [
            {
                "case_id": failure.case_id,
                "grader": failure.grader,
                "score": failure.score,
                "minimum": failure.minimum,
                "notes": failure.notes,
            }
            for failure in report.failures
        ],
    }
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    if not report.ok:
        sys.stderr.write(report.summary() + "\n")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
