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
