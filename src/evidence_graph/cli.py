"""Run one comparison from the terminal: `python -m evidence_graph.cli --countries FR UK`.

The tool mode comes from EVIDENCEGRAPH_TOOL_MODE (fixture, replay, live, record).
"""

import argparse
import sys
from uuid import uuid4

from evidence_graph.config import Settings
from evidence_graph.graph import build_graph, run_comparison
from evidence_graph.state import CountryCode
from evidence_graph.tools.factory import build_toolkit
from evidence_graph.use_cases.ev_incentives import DEFAULT_QUERY, EV_COUNTRIES


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--countries", nargs="+", type=CountryCode, default=list(EV_COUNTRIES))
    parser.add_argument("--query", default=DEFAULT_QUERY)
    args = parser.parse_args(argv)

    settings = Settings()
    graph = build_graph(build_toolkit(settings), settings)
    comparison = run_comparison(graph, settings, args.query, args.countries, str(uuid4()))
    sys.stdout.write(comparison.model_dump_json(indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
