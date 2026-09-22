# 00 — Roadmap

What we are building, what is done, and what is next. Update this file at the end of every
working session.

## Direction

EvidenceGraph is a **generic evidence-gathering graph** with one **pluggable use case**
(EV incentives). Every decision should keep both of these true:

1. The core graph (`graph/`, `tools/`, `state/`) knows nothing about EVs.
2. A new use case is new config under `use_cases/`, not a fork of the graph.

## The production questions and where they get answered

| Question | Answer in one line | Week | Doc |
|---|---|---|---|
| Which agentic pattern, and why? | Map-reduce: parallel, isolated researchers, one comparator | 1 | [05](05-map-reduce.md) |
| How do I manage state across agents? | One typed state; researchers append via a reducer | 1 | [04](04-state.md) |
| How do I restrict which tools each agent can access? | Allowlist wrapper per country; comparator gets no tools | 1–2 | [06](06-tools.md) |
| What happens if one agent or node fails? | Country degrades to `insufficient_evidence`, run continues | 1, 4 | [07](07-reliability.md) |
| How do I validate response quality? | Pydantic schemas, citation checker, quality gate with one retry | 2 | [10](10-evaluation.md) |
| How do I add authentication and authorization? | JWT at the API edge, roles, thread ownership | 3 | [08](08-auth.md) |
| How do I maintain history for multiple users? | Postgres checkpointer keyed by user + thread | 3 | [08](08-auth.md) |
| What if an agent keeps calling the same tool? | Tool-call budget, URL dedupe cache, recursion limit | 4 | [07](07-reliability.md) |
| How do I implement timeouts, fallbacks, stop conditions? | Per-tool, per-country, per-run deadlines; cache fallback | 4 | [07](07-reliability.md) |
| What happens when tool outputs become too large? | Cap in-graph text; full page goes to an artifact store | 4 | [06](06-tools.md) |
| How do I summarize or retrieve only the context I need? | Extract to records early; summarize old turns | 4 | [04](04-state.md) |
| How do I trace every model call, tool call, latency, failure? | OpenTelemetry spans + LangSmith + cost ledger | 5 | [09](09-observability.md) |
| How do I evaluate the complete workflow before production? | Golden dataset + graders + CI gate | 5 | [10](10-evaluation.md) |

## Week 1 — Skeleton (current)

Goal: the full graph shape runs end to end, offline, with tests, before any LLM is added.

- [x] Project setup: `uv`, `pyproject.toml`, `src/` layout, ruff, pytest, Makefile
- [x] Settings from environment (`config.py`)
- [x] Shared contract: `CountryCode`, `Citation`, `IncentiveRecord`, `CountryReport`, `Comparison`
- [x] Graph state with a reducer so parallel researchers can append safely
- [x] Tool contract (`ResearchToolkit` protocol) so real and fixture tools are swappable
- [x] Allowlist policy wrapper, enforced inside `build_graph`, so callers cannot bypass it
- [x] EV use case: four country profiles, official domains, fixture pages
- [x] Graph: planner → `Send` fan-out → researcher ×N → comparator
- [x] Failure isolation: a failing country degrades, the run does not crash
- [x] Checkpointer (`MemorySaver`) and a `thread_id` per request
- [x] API: `GET /health`, `POST /v1/comparisons`
- [x] Tests: fan-out, ordering, dedupe, citations, partial failure, allowlist, API validation
- [x] Learning notebook docs 00–11
- [x] `uv sync`, `pytest` (20 passed), `ruff check`, `ruff format` all green
- [ ] **You:** run `uv run pytest -q` yourself and read each test next to the code it covers
- [ ] **You:** read every doc and rewrite each "four questions" answer in your own words
- [ ] **You:** verify every allowlisted domain is still the correct official source

Definition of done: `pytest` is green, `ruff check` is clean, and you can explain every file.

## Week 2 — Real tools and quality

- [ ] Choose a search provider restricted to allowlisted domains (e.g. site-filtered search API)
- [ ] `tools/http_fetch.py`: real HTTP fetch, content-type checks, size cap
- [ ] `tools/llm_extract.py`: LLM structured output into `IncentiveRecord`
- [ ] Model provider behind an interface, so the model is swappable
- [ ] `tools/registry.py`: explicit map of node → allowed tools
- [ ] `nodes/citations.py`: every claim must point at a fetched URL
- [ ] `nodes/quality_gate.py`: score, retry extraction once, then degrade
- [ ] Record-and-replay fixtures from real pages so tests stay offline
- [ ] Verify each country's current incentive pages by hand; write them into fixtures

## Week 3 — Users

- [ ] `auth/jwt.py`: verify bearer tokens at the API edge
- [ ] `auth/rbac.py`: `viewer` can read threads, `researcher` can start runs
- [ ] `auth/quotas.py`: runs per user per day
- [ ] `memory/checkpointer.py`: `PostgresSaver`, threads owned by `user_id`
- [ ] `api/routes/threads.py`: list, get, delete only your own threads
- [ ] Test: user A cannot read or resume user B's thread
- [ ] Decide multi-turn semantics, then fix the reducer accumulation noted in [04-state](04-state.md)

## Week 4 — Reliability and context

- [ ] `graph/policies.py`: per-tool, per-country, per-run timeouts
- [ ] Retry with backoff on transient tool errors only
- [ ] Tool-call budget per researcher; URL fingerprint cache
- [ ] Fallback to last-good cached report per country
- [ ] `artifacts/store.py`: full page stored by hash; graph sees excerpt only
- [ ] `memory/summarizer.py`: keep recent turns raw, summarize older ones
- [ ] Chaos tests: timeouts, slow tools, oversized pages, repeated URLs

## Week 5 — Observability and evaluation

- [ ] OpenTelemetry spans for every node, tool call, and model call
- [ ] LangSmith tracing for the graph
- [ ] Cost ledger: tokens and USD per run, per user
- [ ] `evals/datasets/goldens.jsonl` with hand-verified expected answers
- [ ] Graders: schema validity, citation faithfulness, no fabricated numbers, latency, cost
- [ ] CI job that fails the merge when graders fall below threshold

## Week 6 — Ship

- [ ] Dockerfile + docker-compose (API, Postgres)
- [ ] Thin UI that renders the comparison table with citations
- [ ] Runbook: what to do when a country source changes or goes down
- [ ] Load test against latency and cost budgets
- [ ] Go / no-go checklist signed off against the production bar below

## Production bar

- Citation coverage of at least 90% of claims
- p95 run latency under 180 seconds
- Cost under $0.40 per comparison
- Zero cross-user thread leaks
- One country failing still returns a comparison
- The comparator can never call the web
- Unauthenticated runs are rejected
