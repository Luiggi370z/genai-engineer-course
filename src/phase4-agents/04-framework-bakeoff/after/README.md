# 4.4 Framework bakeoff — reference

Three tiers, honestly labelled.

**Miniatures** (`src/bakeoff.py`) — each framework's defining idea in ~15 offline
lines: a state machine with a checkpoint, a typed agent that validates first, a
role crew passing context along. For feeling the shape, not for deciding.

**The real tier** (`src/frameworks.py`, `make test-integration`) — the *same*
tool-using agent in LangGraph, Pydantic AI and CrewAI, each returning the same
`Run` shape. One task: look a fact up with a tool, then answer with it.

**The matrix** (`src/matrix.py`) — six dimensions scored from `Measured` rows.

## Why the task is identical across the three

The usual bakeoff gives each library the thing it is best at and concludes what
it assumed. Fixing the task is what makes the residue attributable: same agent,
same assertions in `test_integration.py`, so the differences left over — glue
lines, what survives the process, whether an offline test is even possible —
are the framework's, not the example's.

The single assertion allowed to differ is durability, because it *is* the
finding: `test_only_langgraph_leaves_state_a_second_call_can_resume` reads
`resumable` back out of `get_state` rather than trusting the docs.

Read back by *something else*, which is the part that took a second pass to get
right. The first version built a fresh `MemorySaver` inside `langgraph_run` and
then asked that same compiled app whether it remembered the call it had just
made. It always said yes. The column measured object identity and printed it as
durability. Now the checkpointer is a parameter, a second app over the same
checkpointer takes the reading, and
`test_the_durability_claim_is_measured_across_processes_not_within_one` does it
over SQLite with a closed connection in between — which is what "survives a
crash" has to mean before it goes in a table someone will act on.

## The six dimensions, and why these six

| dimension | measured by | decides |
|---|---|---|
| durability | `Run.resumable`, read back by a DIFFERENT app over the same store | whether you need a database |
| recovery | did a killed run resume | whether a crash costs the user their work |
| complexity | lines of *your* glue | what the next engineer's week looks like |
| observability | spans the run emitted | whether you can debug it at 2am |
| latency | p50 over repeats | whether it ships |
| cost | tokens per run | whether it keeps shipping |

"Nice API" is not here. It is the one everybody rates first and the only one
that stops mattering after a month.

## Read `undecided()` before the winners

On a task this small, several dimensions come back `not distinguished by this
test` — and that is the honest result rather than a gap to fill in. `winner()`
refuses twice: on a tie for the best value, and when the whole spread sits
inside `NOISE_RATIO` (15%). A 4% latency difference is noise, and a matrix is a
persuasive artifact that will outlive everyone's memory of how it was measured.

The skill being taught is reading a ties-heavy matrix and saying either "this
dimension doesn't decide this choice" or "I need a harder test" — instead of
filling all six rows and calling it evidence.

## Verdict template (yours must cite measurements)

LangGraph = durability, branching, human-in-the-loop; the glue is real and buys
you addressable state. Pydantic AI = one typed agent, least ceremony, nothing
survives the process. CrewAI = several collaborating roles; on a single-tool
task it is ceremony, and it is the only one of the three with no offline test
double.

## Concept → framework primitive

| what you built | LangGraph | Pydantic AI | CrewAI |
|---|---|---|---|
| `Graph.nodes` / `edges` / `run` — a hand-rolled state machine | `StateGraph.add_node()` / `add_edge()` / `set_entry_point()` / `compile()` | `Agent.run_sync()` — one typed call, no graph | `Task(..., context=[...])` chains one task's output into the next |
| `self.checkpoint`, overwritten after every node | `MemorySaver` + `app.get_state(config)`, addressable by `thread_id` | — (nothing persists) | — (nothing persists) |
| `TypedAgent.run`'s manual `isinstance` + `raise ValueError` | — (validation lives in the state schema) | `output_type=Answer`, a `BaseModel` | — (roles exchange free text) |
| `crew_style`'s loop over `Worker(role, fn)` | — (edges model handoff between nodes) | — (a single agent) | `Agent(role=..., goal=..., tools=[...])` + `Crew(...).kickoff()` |
| `Recorder.calls` — proof the tool ran | node function calls it directly | `@agent.tool_plain` | `@tool("lookup")` from `crewai.tools` |

## Two traps worth the ink

**`from __future__ import annotations` is deliberately absent from
`frameworks.py`.** It stringifies annotations, which Pydantic AI then resolves
against *module* globals — where a function-local `RunContext` import does not
exist. Lazy imports and postponed annotations do not compose, and the
`NameError` comes from inside the library and names neither cause.

**The topic reaches the Pydantic AI tool through `deps`, not as an argument.**
`TestModel` fills model-chosen arguments with throwaway strings, so a
`lookup(topic: str)` signature yields an agent that looks up `"a"`, returns
`No fact on file.`, and sails past `used_the_tool()`. Values the caller
controls are dependencies; values the model chooses are arguments.

## The CrewAI bound

Python **3.12**, and `qwen3.5:9b` must exist **on the host** (Ollama at
`localhost:11434`). On a newer interpreter CrewAI dies inside Chroma's Pydantic
v1 shim (`unable to infer type for attribute "chroma_server_nofile"`) — a
version bound wearing a library bug's clothes.

So the bound is declared where it binds: `requires-python = ">=3.12,<3.13"` in
this lesson's `pyproject.toml`, which makes `uv sync` fetch a 3.12, and a
`tests/conftest.py` guard that refuses to collect on anything else and names the
interpreter in the failure. The rest of the course is 3.11+. Isolating the pin to
one lesson beats raising the course floor for one framework, and beats a skip
that quietly turns "cannot run" into "passed".

What is still skipped is the model: one pulled into a Docker volume is
unreachable from a host-run test. That skip is a finding — the other two run
offline, while CrewAI constrains the interpreter and cannot be tested without a
live model. That is the observability column, measured.
