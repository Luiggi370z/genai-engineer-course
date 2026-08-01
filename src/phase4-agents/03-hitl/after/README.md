# 4.3 Human-in-the-loop — reference

A durable approval gate: irreversible actions pause, persist, and resume by token —
even across a restart. The framework-free core (`src/hitl.py`) is the fast tier.

`make test-integration` proves the same mechanics in real LangGraph: `interrupt()`
suspends the graph, a checkpointer persists it, `Command(resume=...)` continues it
by `thread_id` — including a restart test where a brand-new graph instance over the
same SQLite checkpoint file picks up the pause and completes it.
