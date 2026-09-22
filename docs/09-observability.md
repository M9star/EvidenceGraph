# 09 — Observability

Status: **week 5**.

## Tracing with OpenTelemetry

**What is it?** A vendor-neutral standard for recording spans: named, timed operations with
attributes, nested under a single trace per request.

**Why do we need it?** A run involves many nodes, tool calls, and model calls. When it is slow
or wrong, we need to know which one.

**What problem does it solve?** It answers **"how do I trace every model call, tool call,
latency, and failure?"** One trace per request, one span per node, tool call, and model call,
each with duration, status, and error.

**What happens if we don't use it?** Debugging means adding print statements and trying to
reproduce the failure, which for a flaky government site may never happen again.

Planned span attributes: `thread_id`, `user_id`, `country`, `node`, `tool`, `url`, `model`,
`input_tokens`, `output_tokens`, `cost_usd`, `status`, `error.type`.

## LangSmith

**What is it?** LangChain's hosted tracing and evaluation tool, with native LangGraph support.

**Why do we need it?** It shows the graph run visually: which node ran, what state it saw, what
it returned, and the exact prompts and outputs of model calls.

**What problem does it solve?** Fast debugging of model behaviour, and a place to turn bad
production traces into eval examples.

**What happens if we don't use it?** You can still use OpenTelemetry alone, but inspecting
prompts and state per step becomes a custom tooling project.

**Design choice:** use both. OpenTelemetry for service-level metrics and alerts in whatever
backend ops uses; LangSmith for agent-level debugging and evals.

## Cost ledger

**What is it?** A record of tokens and USD for every model call, aggregated per run and per user.

**Why do we need it?** The production bar includes cost under $0.40 per comparison.

**What problem does it solve?** It makes cost a measured number, so regressions show up in CI
and in dashboards instead of on the invoice.

**What happens if we don't use it?** Cost creeps up with every prompt change and nobody knows
which change did it.

## Structured logging

**What is it?** JSON logs with the same `trace_id` and `thread_id` as the spans.

**Why do we need it?** Logs and traces must join up during an incident.

**What problem does it solve?** From one error log line you can jump to the full trace.

**What happens if we don't use it?** Free-text logs that cannot be correlated across parallel
researchers running at the same time.

## What must never be logged

- Bearer tokens or API keys.
- Full page contents (store by hash in the artifact store instead).
- Anything a user marks as private in a follow-up question.
