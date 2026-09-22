# 07 — Reliability

## Failure isolation (done in week 1)

**What is it?** Each researcher catches its own errors and returns a `CountryReport` with
status `insufficient_evidence` and the error message.

**Why do we need it?** Some government site will be slow, down, or restructured on any given day.

**What problem does it solve?** It answers **"what happens if one agent or node fails?"**:
three countries still ship, and the output says which one is missing and why.

**What happens if we don't use it?** One exception in the German researcher fails the whole
request, and the user gets nothing.

Tested in [`tests/graph/test_partial_failure.py`](../tests/graph/test_partial_failure.py).

## Recursion limit (done in week 1)

The hard cap on graph steps. See [03-langgraph](03-langgraph.md#recursion_limit).

## Tool-call budget and dedupe (week 4)

**What is it?** A maximum number of tool calls per researcher, plus a cache keyed by a
normalized URL so the same page is never fetched twice in a run.

**Why do we need it?** LLM-driven tool use can repeat the same call when it is unsure.

**What problem does it solve?** It answers **"what if an agent keeps calling the same tool?"**:
the second identical call is a cache hit, and the budget stops runaway loops.

**What happens if we don't use it?** Cost and latency grow with model indecision, and a single
confused run can burn your daily budget.

Week 1 already bounds this without an LLM: `max_pages_per_country` caps fetches.

## Timeouts (week 4)

**What is it?** Deadlines at three levels: per tool call (about 30s), per country (about 90s),
per run (about 180s).

**Why do we need it?** A hanging HTTP request should not hold a user's request open forever.

**What problem does it solve?** Bounded latency. Every level has a known worst case.

**What happens if we don't use it?** Requests hang, workers pile up, and the service falls over
under load because of one slow site.

## Retries with backoff (week 4)

**What is it?** Retrying transient errors (timeouts, 5xx, rate limits) a small number of times
with increasing delays. Never retry policy errors or validation errors.

**Why do we need it?** Many failures are temporary.

**What problem does it solve?** Recovers from blips without user-visible failure.

**What happens if we don't use it?** Every network hiccup becomes a missing country. Retrying
everything, on the other hand, hammers failing sites and retries bugs that will never succeed.

## Fallbacks (week 4)

**What is it?** If a country fails after retries, use the last good report for that country,
clearly marked with its retrieval date. If there is none, degrade to `insufficient_evidence`.

**Why do we need it?** Stale-but-dated evidence is often more useful than nothing.

**What problem does it solve?** Better availability without hiding staleness.

**What happens if we don't use it?** More missing countries. If we fall back without marking
staleness, we mislead users, which is worse.

## Stop conditions (summary)

| Condition | Where | Status |
|---|---|---|
| All requested countries have a report | Graph structure (fan-in) | Week 1 |
| Graph step cap | `recursion_limit` | Week 1 |
| Page cap per country | `max_pages_per_country` | Week 1 |
| Quality gate passes, or fails twice | `quality_gate` node | Week 2 |
| Tool-call budget exhausted | `graph/policies.py` | Week 4 |
| Per-run deadline reached | `graph/policies.py` | Week 4 |
