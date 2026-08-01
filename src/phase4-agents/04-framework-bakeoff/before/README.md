# 4.4 Framework bakeoff

**Goal.** Build the same agent three ways — a mini LangGraph-style state machine,
a typed Pydantic-style agent, a CrewAI-style role crew — so each framework's
defining idea (durability, type-safety, multi-role speed) is something you've felt,
not read. The deliverable is a verdict you can justify out loud.
**Prerequisite.** 4.3 Human-in-the-loop (you've hand-rolled what LangGraph's
checkpointer automates).
**Effort.** ~40 min · gentle

## Do this

```bash
make setup && make test     # 3 failing tests — read them, they are the spec
$EDITOR src/bakeoff.py      # fill TODOs 1-3: langgraph_style, TypedAgent, crew_style
make check                  # green: ruff + pyright + pytest, all offline
```

## What the first failure means

`test_all_three_produce_an_answer` fails because none of the three miniatures is
built yet. Each is ~15 honest lines: `langgraph_style` runs the query through nodes
and checkpoints state after each one, `TypedAgent.run` validates the query before
answering, and `crew_style` has each `Worker` take a turn, passing its output as
the next worker's input.

## Done when

- [ ] `make check` is green (lint, types, fast tests).
- [ ] `TypedAgent.run("")` raises `ValueError` — validation up front is the
      Pydantic-style idea (a test pins this).
- [ ] `crew_style` chains context between roles: two workers turn `"start"` into
      `"start-A-B"` (a test pins this).

## Stuck?

1. The miniatures are deliberately tiny — capture the one defining idea per style,
   not the framework's API. No imports needed beyond what's in the file.
2. For `crew_style`, fold over the workers: feed the query to the first worker's
   `fn`, its output to the next, and return the last output. For `langgraph_style`,
   a dict-as-state plus a list of checkpoint snapshots after each node is enough.

## Going further (optional integration lane)
`make test-integration` proves each idea in the actual libraries: LangGraph's
`StateGraph` + checkpointer resuming by `thread_id`, Pydantic AI returning a
validated model via `TestModel` (both offline), and a two-role CrewAI crew
orchestrated through local Ollama. Needs the opt-in install (LangGraph, Pydantic AI,
CrewAI — a heavy dependency tree) plus Ollama serving `qwen3.5:9b` for the CrewAI
test, which skips cleanly when Ollama is down. Write your verdict from this tier.
Skippable: the fast tier already proves the logic.
