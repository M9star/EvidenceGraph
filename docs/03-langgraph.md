# 03 — LangGraph

Where it lives: [`graph/builder.py`](../src/evidence_graph/graph/builder.py).

## LangGraph

**What is it?** A Python library for building LLM applications as explicit graphs: nodes are
functions, edges are control flow, and a shared typed state moves between them. It adds
checkpointing, parallel branches, and streaming on top.

**Why do we need it?** Our workflow has a fixed shape (plan, research in parallel, merge, check)
with a few controlled loops (retry once). We want that shape to be visible in code and testable,
not hidden inside a prompt.

**What problem does it solve?** It turns "an agent that hopefully does the right steps" into a
program with defined steps, defined state, and defined failure behaviour. You can unit-test a
node, replay a thread, and see exactly which branch ran.

**What happens if we don't use it?** Either one big ReAct agent loops until it decides it is
done (hard to bound, hard to test, easy to hallucinate), or we hand-write our own orchestration,
state merging, checkpointing, and parallelism, which is a framework we then have to maintain.

**Why not Microsoft Agent Framework or Google ADK?** Both can do this. They are strongest when
you are already committed to Azure or Vertex. LangGraph is model- and host-neutral, and its
primitives map one-to-one onto the questions this project is meant to teach.

## StateGraph

**What is it?** The graph builder. You declare a state schema, add nodes, add edges, and
`compile()` it into a runnable.

**Why do we need it?** It enforces that every node reads and writes the same typed state.

**What problem does it solve?** Nodes stay small and independent. A node returns a partial
update (`{"reports": [...]}`), and the graph merges it. No node needs to know who runs next.

**What happens if we don't use it?** Nodes pass ad-hoc dicts to each other, keys drift, and a
typo in one node silently drops data in another.

## `Send` (dynamic fan-out)

**What is it?** A way for a conditional edge to launch the same node many times in parallel,
each with its own input. `fan_out` returns one `Send("researcher", {"country": ...})` per country.

**Why do we need it?** The number of countries comes from the request. We do not want four
hard-coded nodes (`research_fr`, `research_de`, ...).

**What problem does it solve?** One researcher implementation serves any number of countries,
in parallel, and the graph waits for all of them before the comparator runs.

**What happens if we don't use it?** Either sequential research (4× slower) or copy-pasted
nodes per country that drift apart the moment one gets a bug fix.

## Checkpointer and `thread_id`

**What is it?** A checkpointer saves graph state after each step, keyed by a `thread_id`.
Week 1 uses the in-memory `MemorySaver`; week 3 moves to `PostgresSaver`.

**Why do we need it?** Conversation history, resuming after a crash, human review, and
debugging all require the state to be persisted per thread.

**What problem does it solve?** It separates users and conversations: two requests with
different `thread_id`s can never see each other's state.

**What happens if we don't use it?** Every request starts from nothing, there is no history,
a crash mid-run loses all work, and there is no record to debug.

## `recursion_limit`

**What is it?** A hard cap on the number of graph steps in one invocation. Set from
`Settings.recursion_limit` (default 12).

**Why do we need it?** Once we add retry loops in week 2, a bug could make the graph cycle.

**What problem does it solve?** It is the last-resort stop condition. The run fails loudly
instead of burning tokens forever.

**What happens if we don't use it?** A looping graph keeps calling models until someone
notices the bill.
