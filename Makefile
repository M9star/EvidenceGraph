.PHONY: install test lint format run run-live record

install:
	uv sync

test:
	uv run pytest -q

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
