# 02 — Architecture

## Principles

These are the rules that keep the project scalable. If a change breaks one, stop and discuss.

1. **One-way dependencies.** `api → graph → tools → state`. Lower layers never import upper
   layers. The graph never imports FastAPI. Tools never import graph nodes.
2. **Contracts before code.** `state/models.py` is the shared language. Nodes, tools, API, tests,
   and evals all speak it. Change it deliberately.
3. **Policy wraps capability.** Tools do the work; wrappers decide what is allowed. The
   allowlist is applied in `build_graph`, so no caller can get an unwrapped toolkit into a node.
4. **Isolate failure at the smallest unit.** A country failing is a data state
   (`insufficient_evidence`), not an exception that kills the run.
5. **Dependency injection over globals.** `build_graph(toolkit, settings)` takes its
   collaborators. Tests pass fixtures; production passes real tools. Same graph.
6. **Use cases are config.** EV incentives live in `use_cases/ev_incentives/`. A second use
   case should need a new folder, not edits across the graph.
7. **Offline by default.** Tests never touch the live web or a paid model.
8. **Never invent evidence.** No citation, no claim. Missing data is reported as missing.

## Layers

```mermaid
flowchart LR
  subgraph edge[Edge]
    api[api/]
  end
  subgraph core[Core]
    graph[graph/]
    tools[tools/]
    state[state/]
  end
  subgraph domain[Domain]
    uc[use_cases/ev_incentives]
  end
  api --> graph
  graph --> tools
  graph --> state
  tools --> state
  graph --> uc
  uc --> state
```

| Layer | Owns | Must not |
|---|---|---|
| `api/` | HTTP, request validation, thread IDs; later auth and quotas | Call models or tools directly |
| `graph/` | Orchestration: planning, fan-out, merging, gating | Know about HTTP, JWT, SQL |
| `tools/` | Search, fetch, extract, and the policies around them | Decide the final answer |
| `state/` | Data contracts | Contain behaviour |
| `use_cases/` | Countries, domains, prompts, fixtures | Change graph wiring |

## Request lifecycle (week 1)

1. `POST /v1/comparisons` validates the body and creates a `thread_id`.
2. `run_comparison` invokes the compiled graph with a recursion limit.
3. The **planner** validates and deduplicates the requested countries.
4. `fan_out` emits one `Send("researcher", {...})` per country. They run in parallel.
5. Each **researcher** calls `search → fetch → extract` through the allowlisted toolkit and
   returns one `CountryReport`. Errors become `insufficient_evidence`.
6. The `reports` reducer appends all four reports into shared state.
7. The **comparator** orders reports and lists missing countries. It has no tools.
8. The API returns `{thread_id, comparison}`.

## Folder map

```text
src/evidence_graph/
  config.py                      Settings (env prefix EVIDENCEGRAPH_)
  api/main.py                    create_app(settings, toolkit): the composition root
  api/deps.py                    Pulls graph/settings off app.state
  api/routes/compare.py          POST /v1/comparisons
  api/routes/health.py           GET /health
  graph/builder.py               build_graph + run_comparison
  graph/nodes/planner.py         plan + fan_out (Send)
  graph/nodes/researcher.py      One worker, parameterized by country
  graph/nodes/comparator.py      Merge, order, list missing
  tools/base.py                  ResearchToolkit protocol, errors, SearchHit, FetchedPage
  tools/policy.py                is_allowed + AllowlistedToolkit
  tools/fixture.py               Offline toolkit for tests and local runs
  state/models.py                Pydantic contracts
  state/graph_state.py           ResearchState, ResearchTask
  use_cases/ev_incentives/       Country profiles, allowlists, fixtures
```

## Why `create_app` is a factory

**What is it?** A function that builds and returns the FastAPI app, instead of a module-level
app configured at import time.

**Why do we need it?** Tests need to build an app with a fixture toolkit; production needs one
with real tools. A factory lets both happen without monkeypatching.

**What problem does it solve?** It gives the project one composition root: the only place that
decides which concrete tools, checkpointer, and settings are wired together.

**What happens if we don't use it?** Tests start patching globals, import order starts to
matter, and one day a test hits a real API because a global was not patched.
