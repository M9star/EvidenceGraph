.PHONY: install test test-live lint format run run-live record secrets-check

install:
	uv sync
	@# Copy hooks into .git/hooks so commit and push scan for secrets.
	@# Does not change git config. Safe to re-run.
	@mkdir -p .git/hooks
	@cp .githooks/pre-commit .githooks/pre-push .githooks/commit-msg .git/hooks/
	@chmod +x .git/hooks/pre-commit .git/hooks/pre-push .git/hooks/commit-msg
	@echo "installed git hooks: pre-commit, pre-push, commit-msg"

test:
	uv run pytest -q

# One real Tavily call. Needs EVIDENCEGRAPH_TAVILY_API_KEY in .env.
test-live:
	uv run pytest -q --live tests/tools/test_search.py::test_tavily_live_returns_https_hits_on_the_uk_allowlist

lint:
	uv run ruff check src tests

format:
	uv run ruff format src tests

run:
	uv run uvicorn evidence_graph.api.main:app --reload

run-live:
	EVIDENCEGRAPH_TOOL_MODE=live uv run uvicorn evidence_graph.api.main:app --reload

# Hits the live web and the local model, then overwrites tests/fixtures/recorded/.
# Review the diff by hand before committing: recordings become test truth.
record:
	EVIDENCEGRAPH_TOOL_MODE=record uv run python -m evidence_graph.cli

# Fail if a tracked file looks like a secret. Run before you push.
secrets-check:
	python3 scripts/check_secrets.py tree
