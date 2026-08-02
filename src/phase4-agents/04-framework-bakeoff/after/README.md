# 4.4 Framework bakeoff — reference

Two tiers. The fast tier (`src/bakeoff.py`) is the same agent as a mini LangGraph
state machine, a typed Pydantic-style agent, and a CrewAI-style role crew — offline
miniatures, honestly labelled, that capture each defining idea in ~15 lines.

The real tier (`make test-integration`) proves each idea in the actual library:
LangGraph's `StateGraph` + checkpointer resuming by `thread_id`, Pydantic AI
returning a validated model via `TestModel` (offline), and a two-role CrewAI crew
orchestrated through local Ollama.

**Verdict template:** LangGraph = durability/branching/HITL (production default);
Pydantic AI = type-safe single agent, minimal ceremony; CrewAI = fast role-based
multi-agent prototyping. Choose by your dominant constraint.

## Concept → framework primitive

| what you built | LangGraph | Pydantic AI | CrewAI |
|---|---|---|---|
| `Graph.nodes` / `Graph.edges` / `Graph.run` — a hand-rolled state machine | `StateGraph.add_node()` / `add_edge()` / `set_entry_point()` / `compile()` | `Agent.run_sync()` — one typed call, no graph at all | `Task(..., context=[...])` chains one task's output into the next |
| `self.checkpoint`, overwritten after every node | `MemorySaver` checkpointer + `app.get_state(config)`, addressable by `thread_id` | — (no built-in checkpointing) | — (no built-in checkpointing) |
| `TypedAgent.run`'s manual `isinstance` check + `raise ValueError` | — (validation lives in the state schema, not per call) | `output_type=Answer`, a `BaseModel` — a malformed reply fails loudly instead of flowing downstream | — (roles exchange free text, no schema) |
| `crew_style`'s `for w in workers` loop over `Worker(role, fn)` | — (edges model handoff between nodes, not roles) | — (a single agent, no role concept) | `Agent(role=..., goal=..., backstory=..., llm=...)` + `Crew(agents=[...], tasks=[...]).kickoff()` |

**Two artifacts.** You now own two things that prove different skills: the three
~15-line miniatures in `bakeoff.py` prove you understand what each framework's
defining idea actually *does* underneath — a checkpoint, a validated model, a
role handoff — and the tests in `test_integration.py` prove you can drive the
real `StateGraph`, `Agent`, and `Crew` APIs to get that same behavior out of a
production library. The interview skill is being able to point at
`self.checkpoint` and say "that's what `MemorySaver` gives you for free" —
this table is that explanation written down.
