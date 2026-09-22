# 11 — Supporting stack

The non-agent technologies in week 1, with the same four questions.

## uv

**What is it?** A fast Python package and project manager: virtualenvs, dependency resolution,
lockfile, and running commands (`uv sync`, `uv run pytest`).

**Why do we need it?** Everyone, including CI, must install the exact same dependency versions.

**What problem does it solve?** Reproducible environments from `pyproject.toml` plus `uv.lock`,
in seconds.

**What happens if we don't use it?** "Works on my machine": a transitive dependency updates and
LangGraph behaviour changes between your laptop and CI.

## `src/` layout

**What is it?** Package code lives in `src/evidence_graph/` instead of at the repo root.

**Why do we need it?** Tests should import the installed package, the way production does.

**What problem does it solve?** It prevents tests from accidentally passing because they
imported a file from the working directory that is not actually part of the package.

**What happens if we don't use it?** Packaging bugs show up only after deployment.

## FastAPI

**What is it?** A Python web framework built on type hints and Pydantic.

**Why do we need it?** The agent needs an HTTP API for UIs, other services, and auth.

**What problem does it solve?** Request validation (unknown country → 422), response schemas,
dependency injection for auth later, and automatic OpenAPI docs at `/docs`.

**What happens if we don't use it?** Hand-written validation, no generated docs, and auth
checks scattered through handlers.

## Uvicorn

**What is it?** The ASGI server that runs the FastAPI app.

**Why do we need it?** FastAPI is a framework, not a server.

**What problem does it solve?** It serves HTTP efficiently and supports multiple workers.

**What happens if we don't use it?** Nothing serves the app.

## pydantic-settings

**What is it?** Loads typed configuration from environment variables and `.env`, with validation.

**Why do we need it?** Limits, modes, and later API keys must differ between local, CI, and prod
without code changes.

**What problem does it solve?** Bad config fails at startup (`recursion_limit=0` is rejected),
not halfway through a user request.

**What happens if we don't use it?** `os.getenv` calls everywhere, string-typed numbers, and
secrets accidentally committed in code.

## Ruff

**What is it?** A fast Python linter and formatter.

**Why do we need it?** Consistent style and early detection of common bugs.

**What problem does it solve?** Code review focuses on design instead of formatting, and
unused imports or shadowed names are caught automatically.

**What happens if we don't use it?** Style drifts, diffs get noisy, and small bugs slip through.

## httpx

**What is it?** An HTTP client. FastAPI's `TestClient` uses it.

**Why do we need it?** API tests in week 1; live fetch tool in week 2.

**What problem does it solve?** One client for tests and production, with timeouts and async
support.

**What happens if we don't use it?** API tests need a running server, and fetch code lacks
sane timeout defaults.
