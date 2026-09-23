#!/usr/bin/env python3
"""Block commits and pushes that contain secrets or files that must stay local.

  python3 scripts/check_secrets.py staged        # what `git commit` is about to record
  python3 scripts/check_secrets.py push < refs   # commits `git push` is about to send
  python3 scripts/check_secrets.py tree          # every tracked file right now
  python3 scripts/check_secrets.py history       # every commit reachable from HEAD

A line containing `secret-scan: allow` is skipped, for deliberate test fixtures only.
Standard library only, so it runs before `uv sync`.
"""

import re
import subprocess
import sys
from fnmatch import fnmatch

ZERO_SHA = "0" * 40
ALLOW_MARKER = "secret-scan: allow"

FORBIDDEN_PATHS = (
    ".env",
    ".env.*",
    "*/.env",
    "*/.env.*",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "*.keystore",
    "id_rsa*",
    "id_ed25519*",
    "*credentials*.json",
    "*service-account*.json",
    "secrets/*",
)
ALLOWED_PATHS = (".env.example",)

# Only enforced on new commits: older commits already contain docs/.
LOCAL_ONLY_PATHS = ("docs/*", "notes/*")

SECRET_PATTERNS = {
    "Tavily API key": r"tvly-[A-Za-z0-9_-]{16,}",
    "OpenAI API key": r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}",
    "Anthropic API key": r"sk-ant-[A-Za-z0-9_-]{20,}",
    "LangSmith API key": r"lsv2_[a-z]{2}_[A-Za-z0-9]{20,}",
    "GitHub token": r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}",
    "AWS access key": r"(?:AKIA|ASIA)[A-Z0-9]{16}",
    "Google API key": r"AIza[0-9A-Za-z_-]{35}",
    "Slack token": r"xox[abprs]-[A-Za-z0-9-]{10,}",
    "Private key": r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----",
    "Secret assigned in env style": (
        r"\b[A-Z0-9_]*(?:API_KEY|SECRET|TOKEN|PASSWORD)[A-Z0-9_]*\s*=\s*"
        r"['\"]?(?!(?i:your|changeme|example|xxx|\.\.\.))[A-Za-z0-9_\-/+=.]{16,}"
    ),
    "Credentials in URL": r"[a-z][a-z0-9+.-]*://[^\s:/@]+:[^\s:/@]{6,}@",
}
_COMPILED = {name: re.compile(pattern) for name, pattern in SECRET_PATTERNS.items()}


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True, errors="replace"
    ).stdout


def path_problems(paths: list[str], check_local_only: bool) -> list[str]:
    problems = []
    for path in sorted(set(paths)):
        name = path.rsplit("/", 1)[-1]
        if path in ALLOWED_PATHS or name in ALLOWED_PATHS:
            continue
        if any(fnmatch(path, p) or fnmatch(name, p) for p in FORBIDDEN_PATHS):
            problems.append(f"{path}: file type must never be committed")
        elif check_local_only and any(fnmatch(path, p) for p in LOCAL_ONLY_PATHS):
            problems.append(f"{path}: local-only (gitignored) folder")
    return problems


def line_problems(where: str, line: str) -> list[str]:
    if ALLOW_MARKER in line:
        return []
    return [f"{where}: possible {name}" for name, rx in _COMPILED.items() if rx.search(line)]


def diff_problems(diff: str) -> list[str]:
    """Scan only added lines of a unified diff, tracking which file and commit they belong to."""
    problems, current_file, commit = [], "?", ""
    for line in diff.splitlines():
        if line.startswith("commit "):
            commit = line.split()[1][:8] + " "
        elif line.startswith("+++ "):
            current_file = line[6:] if line.startswith("+++ b/") else line[4:]
        elif line.startswith("+") and not line.startswith("+++"):
            problems += line_problems(f"{commit}{current_file}", line[1:])
    return problems


def check_staged() -> list[str]:
    paths = git("diff", "--cached", "--name-only", "--diff-filter=ACMR").split()
    diff = git("diff", "--cached", "-U0", "--no-color", "--diff-filter=ACMR")
    return path_problems(paths, check_local_only=True) + diff_problems(diff)


def check_range(rev_args: list[str]) -> list[str]:
    paths = git("log", "--name-only", "--format=", "--diff-filter=ACMR", *rev_args).split()
    diff = git("log", "-p", "-U0", "--no-color", "--format=commit %H", *rev_args)
    return path_problems(paths, check_local_only=False) + diff_problems(diff)


def check_push(stdin: str) -> list[str]:
    problems = []
    for line in stdin.splitlines():
        parts = line.split()
        if len(parts) != 4 or parts[1] == ZERO_SHA:
            continue  # malformed, or deleting a remote branch
        local_sha, remote_sha = parts[1], parts[3]
        if remote_sha == ZERO_SHA:
            rev_args = [local_sha, "--not", "--remotes"]
        else:
            rev_args = [f"{remote_sha}..{local_sha}"]
        problems += check_range(rev_args)
    return problems


def check_tree() -> list[str]:
    problems = path_problems(git("ls-files").split(), check_local_only=True)
    for path in git("ls-files").split():
        try:
            with open(path, encoding="utf-8", errors="ignore") as handle:
                for number, line in enumerate(handle, 1):
                    problems += line_problems(f"{path}:{number}", line)
        except (IsADirectoryError, FileNotFoundError):
            continue
    return problems


def main(argv: list[str]) -> int:
    mode = argv[1] if len(argv) > 1 else "staged"
    if mode == "staged":
        problems = check_staged()
    elif mode == "push":
        problems = check_push(sys.stdin.read())
    elif mode == "tree":
        problems = check_tree()
    elif mode == "history":
        problems = check_range(["HEAD"])
    else:
        print(__doc__, file=sys.stderr)
        return 2

    if not problems:
        return 0
    print(f"\nsecret-scan blocked this {mode} check:\n", file=sys.stderr)
    for problem in dict.fromkeys(problems):
        print(f"  - {problem}", file=sys.stderr)
    print(
        "\nRemove the secret (keep it in .env), unstage the file, or, for a deliberate fake\n"
        f"test value, add '{ALLOW_MARKER}' to that line. If a real key was ever committed,\n"
        "revoke it with the provider: deleting it in a later commit does not remove it.\n",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
