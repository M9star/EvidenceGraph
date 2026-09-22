.PHONY: install test lint format run

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
