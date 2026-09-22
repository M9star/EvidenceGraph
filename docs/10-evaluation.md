# 10 — Evaluation and quality

## Tests vs evals

| | Tests (`tests/`) | Evals (`evals/`, week 5) |
|---|---|---|
| Checks | Code behaviour | Answer quality |
| Uses | Fixtures, no model | Real or recorded model outputs |
| Result | Pass or fail | Scores against thresholds |
| Runs | Every commit | Every PR touching prompts, models, tools |

Both are required. Tests prove the graph behaves; evals prove the answers are good.

## pytest (done in week 1)

**What is it?** Python's standard test runner.

**Why do we need it?** Every production question has a behaviour we can assert.

**What problem does it solve?** It locks in guarantees: partial failure, allowlist enforcement,
ordering, validation. A refactor that breaks one fails immediately.

**What happens if we don't use it?** Guarantees exist only in the docs, and they quietly stop
being true.

Week 1 tests:

| Test | Guarantee |
|---|---|
| `test_fan_out.py` | Every country researched, merged in order, deduplicated, cited |
| `test_partial_failure.py` | One or all countries failing still returns a comparison |
| `test_allowlist_policy.py` | Off-list and lookalike domains are blocked end to end |
| `test_comparisons_api.py` | API contract, validation, one thread per request |

## Response validation (week 2)

Three layers, cheapest first:

1. **Schema:** Pydantic rejects malformed records and uncited incentives.
2. **Citation checker:** every claim's text must be supported by the fetched page it cites.
3. **Quality gate:** scores completeness and consistency. Below threshold: retry extraction
   once. Still below: return the evidence without a synthesized comparison.

**What happens if we don't validate?** The system returns fluent, confident, wrong answers,
which is the default failure mode of LLMs.

## Golden dataset (week 5)

**What is it?** A small set (start with 20) of requests with hand-verified expected facts and
source URLs, stored in `evals/datasets/goldens.jsonl`.

**Why do we need it?** Quality needs a fixed reference, or every change is judged by vibes.

**What problem does it solve?** It answers **"how do I evaluate the complete workflow before
production?"**: run the whole graph against goldens and compare.

**What happens if we don't use it?** Prompt tweaks that fix one case silently break three others.

**Important:** incentive policies change. Each golden records the date it was verified, and
goldens older than a set age must be re-verified.

## Graders (week 5)

| Grader | Type | Threshold (initial) |
|---|---|---|
| Schema validity | Code | 100% |
| Citation coverage | Code | ≥ 90% of claims |
| Citation faithfulness | LLM-as-judge, spot-checked by a human | ≥ 90% |
| No fabricated numbers | Code: every number appears in the cited page | 100% |
| Latency p95 | Code | < 180s |
| Cost per run | Code | < $0.40 |

## CI gate (week 5)

Tests run on every commit. Evals run on every PR that touches `graph/`, `tools/`, prompts, or
model config. A PR cannot merge if any grader drops below threshold.
