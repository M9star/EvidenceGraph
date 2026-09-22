# 04 — State

Where it lives: [`state/models.py`](../src/evidence_graph/state/models.py) and
[`state/graph_state.py`](../src/evidence_graph/state/graph_state.py).

## Pydantic models

**What is it?** Python classes that validate data at runtime: types, required fields,
constraints like `min_length=1`.

**Why do we need it?** LLM output and web content are untrusted. The first place bad data
should fail is the boundary where it enters our system.

**What problem does it solve?** `IncentiveRecord.citations` has `min_length=1`, so an incentive
without a citation cannot exist in our system. The contract enforces a product rule.

**What happens if we don't use it?** Uncited or malformed records flow through to the user, and
we find out from a screenshot on social media.

## Graph state (`ResearchState`)

**What is it?** A `TypedDict` describing everything the graph knows during a run: `query`,
`countries`, `reports`, `comparison`.

**Why do we need it?** It is the single source of truth that all nodes read and write.

**What problem does it solve?** Agents coordinate through data, not through each other. The
researcher does not call the comparator; it writes a report, and the comparator reads reports.

**What happens if we don't use it?** Agents pass messages directly, coupling grows, and adding
a node means editing every node that talks to it.

## Reducers (`Annotated[list[CountryReport], operator.add]`)

**What is it?** A rule for how concurrent updates to one state key are combined. `operator.add`
concatenates lists.

**Why do we need it?** Four researchers run in the same step and all write to `reports`.

**What problem does it solve?** Parallel writes are appended instead of overwriting each other.

**What happens if we don't use it?** Last writer wins: you get one country in the output and
three silently lost. (LangGraph actually raises an error for conflicting concurrent writes to a
plain key, which is better than silent loss but still a crash.)

## `ResearchTask` (the per-branch input)

**What is it?** A small `TypedDict` with just `query` and `country`, sent to each researcher.

**Why do we need it?** A researcher should only see what it needs for its own country.

**What problem does it solve?** Least privilege for data: a researcher cannot read or modify
another country's report.

**What happens if we don't use it?** Every branch sees the whole state, and a bug in one branch
can corrupt another's output.

## Lesson from week 1: state must be serializable

The first test run failed with `TypeError: Type is not msgpack serializable: CountryReport`.

The cause was `Citation.url: HttpUrl`. The checkpointer saves state with msgpack after every
step. `model_dump()` keeps `HttpUrl` as a pydantic `Url` object, and msgpack cannot encode it.

The fix is the `SourceUrl` type in `models.py`: it still validates as `HttpUrl` on the way in,
but serializes as a plain `str`.

The rule: **everything in graph state must survive a checkpoint round trip.** Prefer plain
types (`str`, `int`, `datetime`, enums, lists, nested Pydantic models of those). Every node
test that runs through the compiled graph also exercises the checkpointer, which is how this
got caught before production.

## Known issue for week 3: reports accumulate on a reused thread

Because `reports` uses `operator.add` and the checkpointer persists state, invoking the graph
twice on the **same** `thread_id` appends a second set of reports to the first. Week 1 avoids
this by creating a new `thread_id` per request.

Before multi-turn conversations in week 3, decide the semantics. Options:

- Store each run's results under a `run_id` key instead of one growing list.
- Use a custom reducer that replaces reports for a country when a new run starts.
- Keep a separate `history` channel for conversation turns and reset `reports` per run.

## Context management (week 4)

The rule: **extract early, keep the graph small.** Raw pages never live in state long-term.
Researchers turn pages into `IncentiveRecord`s immediately. Full page text will go to an
artifact store, keyed by hash, and state keeps only the excerpt and URL. Conversation history
keeps the last few turns raw and summarizes older ones.
