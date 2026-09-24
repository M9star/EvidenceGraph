# EvidenceGraph

**Cited, fault-tolerant multi-agent research with LangGraph.**

EvidenceGraph answers research questions by fanning out to isolated agents, collecting
evidence only from trusted sources, and returning one structured answer where every claim
carries a citation.

The first use case:

> Compare the latest EV incentives available in France, Germany, the UK, and India.
> Search official government or trusted sources for each country, extract the eligibility
> rules and benefits, and return one consolidated comparison with citations.

This is a learning project with a production bar. The goal is not a demo. The goal is to be
able to answer, with running code and tests, every question in
[`docs/00-roadmap.md`](docs/00-roadmap.md).

## Status

**Week 4 done. Next: week 5 (observability).** Runs are bounded: tool/country/run
deadlines, retries only on transient errors, a per-researcher tool budget, and a URL cache.
Full pages go to an artifact store; old conversation turns are summarized. Tracing and evals
are next.

## Quick start

```bash
uv sync
make install                # also installs git hooks that block secrets on commit/push
uv run pytest -q
make run                    # offline placeholder tools
EVIDENCEGRAPH_TOOL_MODE=replay make run   # offline, recorded real pages
make run-live               # live web + local model (needs `ollama pull llama3.1:8b`)
```

Copy `.env.example` to `.env` and put API keys only in `.env`. That file is gitignored.
`make install` installs hooks that refuse to commit or push `.env`, key files, or strings
that look like API keys. `make secrets-check` scans every tracked file the same way.

| `EVIDENCEGRAPH_TOOL_MODE` | Search | Fetch | Extract |
|---|---|---|---|
| `fixture` (default) | canned | canned | canned placeholders |
| `replay` | recorded | recorded | recorded |
| `live` | Tavily, or seed URLs without a key | HTTP | Ollama |
| `record` | as `live`, and writes `tests/fixtures/recorded/` | | |

```bash
# .env must set EVIDENCEGRAPH_JWT_SECRET (see .env.example). Then:
TOKEN=$(uv run python -m evidence_graph.auth --user local --role researcher)
curl -s -X POST localhost:8000/v1/comparisons \
  -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{}'
```

## How it works

```mermaid
flowchart TD
  api[POST /v1/comparisons] --> planner[Planner]
  planner -->|Send| fr[Researcher: FR]
  planner -->|Send| de[Researcher: DE]
  planner -->|Send| uk[Researcher: UK]
  planner -->|Send| in[Researcher: IN]
  fr --> comparator[Comparator]
  de --> comparator
  uk --> comparator
  in --> comparator
  comparator --> response[Comparison with citations]
```

Each researcher can only reach its own country's official domains. If one researcher fails,
that country is marked `insufficient_evidence` and the rest of the comparison still ships.

## Layout

```text
src/evidence_graph/
  api/          HTTP edge: routes, dependencies. Auth and thread ownership live here.
  auth/         JWT verify, roles, quotas. No FastAPI.
  memory/       Checkpointer, thread store, last-good reports, history summarizer.
  artifacts/    Full page text by hash. Graph and models see an excerpt.
  graph/        LangGraph: builder + nodes. Owns reasoning. policies.py = deadlines and budgets.
  tools/        Tool contract, allowlist, registry, search, fetch, extract. Owns the web.
  llm/          Model interface + Ollama. Used only by tools.
  state/        Pydantic models + graph state. The shared contract.
  use_cases/    Domain config. ev_incentives/ = countries, allowlists, fixtures.
  config.py     Settings from environment.
tests/          Offline tests. Never hit the live web. fixtures/recorded/ = replayed live run.
docs/           Learning notebook + roadmap.
```

The dependency direction is one way: `api → graph → tools → (llm, state)`. The graph never imports
FastAPI or parses JWTs. Tools never decide the final answer. The use case plugs in config, not code paths.

## Learning notebook

These notes live in a local, untracked `docs/` folder and are not part of the repository.

| Doc | Topic |
|---|---|
| [00-roadmap](docs/00-roadmap.md) | What is done, what is next, week by week |
| [01-problem](docs/01-problem.md) | Problem, scope, non-goals, success criteria |
| [02-architecture](docs/02-architecture.md) | Principles, layers, dependency rules |
| [03-langgraph](docs/03-langgraph.md) | LangGraph, StateGraph, Send, checkpointers |
| [04-state](docs/04-state.md) | Typed state, Pydantic, reducers |
| [05-map-reduce](docs/05-map-reduce.md) | Why this agentic pattern, and what we rejected |
| [06-tools](docs/06-tools.md) | Tool contracts, allowlists, fixtures |
| [07-reliability](docs/07-reliability.md) | Failure isolation, loops, timeouts, fallbacks |
| [08-auth](docs/08-auth.md) | Authentication, authorization, multi-user history |
| [09-observability](docs/09-observability.md) | Tracing, tokens, latency, cost |
| [10-evaluation](docs/10-evaluation.md) | Tests vs evals, goldens, CI gates |
| [11-stack](docs/11-stack.md) | FastAPI, uv, pytest, ruff, pydantic-settings |

Every technology in these docs answers four questions: **What is it? Why do we need it? What
problem does it solve? What happens if we don't use it?**
