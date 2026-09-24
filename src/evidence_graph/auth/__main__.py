"""Mint a local JWT: `uv run python -m evidence_graph.auth --user alice --role researcher`."""

import argparse
import sys

from evidence_graph.auth.jwt import AuthError, Role, mint_access_token
from evidence_graph.config import Settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user", required=True)
    parser.add_argument("--role", default=Role.RESEARCHER.value, choices=[r.value for r in Role])
    parser.add_argument("--ttl", type=int, default=3600)
    args = parser.parse_args(argv)

    try:
        token = mint_access_token(Settings(), args.user, args.role, ttl_s=args.ttl)
    except AuthError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1
    sys.stdout.write(token + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
