import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "check_secrets", ROOT / "scripts" / "check_secrets.py"
)
assert SPEC and SPEC.loader
check_secrets = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check_secrets)


@pytest.mark.parametrize(
    "path",
    [".env", "src/.env", ".env.local", "id_rsa", "service-account.json", "secrets/tavily.txt"],
)
def test_secret_filenames_are_forbidden(path):
    problems = check_secrets.path_problems([path], check_local_only=True)

    assert problems


def test_env_example_is_allowed():
    assert check_secrets.path_problems([".env.example"], check_local_only=True) == []


def test_local_only_folders_are_blocked_on_new_commits():
    problems = check_secrets.path_problems(["docs/00-roadmap.md", "notes/progress.md"], True)

    assert len(problems) == 2


def test_tavily_key_shape_is_caught():
    fake = "tvly-" + ("x" * 20)  # secret-scan: allow
    line = f"EVIDENCEGRAPH_TAVILY_API_KEY={fake}"

    problems = check_secrets.line_problems("x", line)

    assert any("Tavily" in problem for problem in problems)


def test_allow_marker_skips_a_deliberate_fixture_line():
    line = "tvly-" + ("x" * 20) + "  # secret-scan: allow"

    assert check_secrets.line_problems("x", line) == []


def test_placeholder_env_example_line_is_not_a_secret():
    line = "# EVIDENCEGRAPH_TAVILY_API_KEY="

    assert check_secrets.line_problems(".env.example", line) == []


def test_added_secret_in_a_diff_is_caught():
    fake = "tvly-" + ("x" * 20)  # secret-scan: allow
    diff = f"+++ b/src/evidence_graph/config.py\n+TAVILY_API_KEY={fake}\n unchanged\n-old\n"

    problems = check_secrets.diff_problems(diff)

    assert any("Tavily" in problem for problem in problems)
