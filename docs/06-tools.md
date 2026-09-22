# 06 — Tools

Where it lives: [`tools/`](../src/evidence_graph/tools/).

## Tool contract (`ResearchToolkit` protocol)

**What is it?** A Python `Protocol` that says any toolkit must provide `search`, `fetch`, and
`extract`, each taking a `country`.

**Why do we need it?** We want to swap fixture tools, recorded tools, and live tools without
touching the graph.

**What problem does it solve?** The graph depends on an interface, not a vendor. Changing the
search provider or the extraction model is a new class, not a refactor.

**What happens if we don't use it?** Search-API and model-SDK calls get written directly inside
nodes. Tests need network access, and switching vendors means rewriting nodes.

## Allowlist policy (`AllowlistedToolkit`)

**What is it?** A wrapper around any toolkit. It drops search hits outside the country's
official domains and refuses to fetch or extract from them. `is_allowed` requires `https` and
an exact domain or subdomain match.

**Why do we need it?** The brief says "official government or trusted sources". That has to be
enforced by code, not requested in a prompt.

**What problem does it solve?** It answers **"how do I restrict which tools each agent can
access?"** at the data level: the UK researcher physically cannot read a German site or a
dealer blog. It also blocks lookalike domains such as `gov.uk.evil.example`.

**What happens if we don't use it?** A search result from a car-dealer blog gets extracted,
cited, and presented as government policy.

**Why a wrapper and not a check inside each tool?** Policy in one place is auditable and
testable once. `build_graph` applies it, so no caller can skip it by accident.

## Tool access per node

| Node | Tools | Why |
|---|---|---|
| planner | none | Only validates the request |
| researcher | `search`, `fetch`, `extract` for its own country | Needs evidence |
| comparator | none | Must only use evidence already collected |
| citation checker (week 2) | none | Checks claims against collected sources |
| quality gate (week 2) | none | Scores; does not browse |

Week 2 makes this table executable in `tools/registry.py`.

## Fixture toolkit (`FixtureToolkit`)

**What is it?** An offline toolkit that returns canned pages from
`use_cases/ev_incentives/fixtures.py`. It can simulate failure with `fail_on={CountryCode.DE}`.

**Why do we need it?** Tests must be fast, free, deterministic, and runnable on a plane.

**What problem does it solve?** We can test graph behaviour (fan-out, failure isolation,
policy) separately from model and network behaviour.

**What happens if we don't use it?** Tests are slow, cost money, fail when a site is down, and
give different results on every run, so nobody trusts them.

**Important:** fixture pages are placeholders. They are not real incentive data and must never
be shown to users as such.

## Large tool outputs (week 4)

**What is it?** A cap on how much page text enters graph state, plus an artifact store for the
full page, keyed by content hash.

**Why do we need it?** Government pages can be tens of thousands of tokens.

**What problem does it solve?** It keeps model calls within context limits and cost budgets,
while keeping the full source available for citation checks and audits.

**What happens if we don't use it?** Context overflow errors, huge bills, and models that
ignore the relevant paragraph because it is buried in navigation menus.

## Live tools (week 2)

- **Search:** a provider that supports domain filtering, so the allowlist is applied at query
  time as well as after.
- **Fetch:** HTTP client with timeouts, content-type checks, redirect limits, and a size cap.
  Redirects must be checked against the allowlist too.
- **Extract:** LLM with structured output into `IncentiveRecord`. It must only use the page it
  was given, and every field must be traceable to that page.
