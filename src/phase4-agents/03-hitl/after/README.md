# 4.3 Human-in-the-loop — reference

A durable approval gate: irreversible actions pause, persist, and resume by token —
even across a restart. Both implementations live in `src/hitl.py`: `Runner` is the
framework-free core on the fast tier, `approval_graph` is the same thing in real
LangGraph.

`make test-integration` runs the graph: `interrupt()` suspends it, a checkpointer
persists it, `Command(resume=...)` continues it by `thread_id` — including a
restart test where a brand-new graph instance over the same SQLite checkpoint file
picks up the pause and completes it.

## Concept → framework primitive

| what you built | the primitive in LangGraph | what the framework adds |
|---|---|---|
| `Runner.act()` pausing on an `IRREVERSIBLE` action, returning a `PendingApproval` | `interrupt()` called inside a graph node (`approve`) | suspension is first-class graph state, not a sentinel object you have to check for |
| `self._pending` dict, hand-serialized via `_save()` / `_load()` to a JSON file | a `checkpointer` (`MemorySaver`, `SqliteSaver`) passed to `graph.compile(checkpointer=...)` | pluggable, swappable persistence backends — no hand-rolled (de)serialization |
| `resume(token, approved)` popping the entry out of `_pending` | `Command(resume=...)` passed to `app.invoke()` | resume routes back into the exact suspended node, rather than re-running from scratch |
| the `token` string keying `_pending` | `thread_id` inside `config["configurable"]` | one id addresses the whole graph run, not just a single paused action |
| restart-safety via a `Path(store)` JSON round-trip | `SqliteSaver` over a real SQLite connection, exercised by a two-process test | durability proven across a process crash, not just a re-read of a file |

**Two artifacts, both yours.** `Runner` proves you understand the mechanism — why
a pause has to be persisted, not just held in memory, before you can call it
durable. `approval_graph` proves you can operate the real tool: `interrupt()`, a
checkpointer, and `Command(resume=...)` wired into something that survives an
actual restart. The graph used to live in the test file, which meant the
framework half of this lesson was something you read; the tests now drive your
module, and the two placement mistakes that pass a casual reading — interrupting
inside the sending node, gating on a flag rather than on a value the pause
produces — fail them.

The interview skill is explaining that `self._pending`'s JSON file and LangGraph's
`SqliteSaver` are the same idea at two levels of production-readiness.
