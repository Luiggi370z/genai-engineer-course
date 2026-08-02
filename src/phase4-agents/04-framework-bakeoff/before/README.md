# 4.4 Framework bakeoff

**Goal.** Run the *same* tool-using agent through LangGraph, Pydantic AI and
CrewAI, measure six things about each run, and let a matrix derive the verdict.
Not "which framework is best" — which one your constraint picks, and which
dimensions your test was too small to decide.
**Prerequisite.** 4.3 Human-in-the-loop (you've hand-rolled what LangGraph's
checkpointer automates).
**Effort.** ~75 min · moderate

## Do this

```bash
make setup && make test      # red — read the failures, they are the spec
$EDITOR src/bakeoff.py       # TODOs 1-3: the offline miniatures
$EDITOR src/matrix.py        # TODOs 1-4: scoring, offline, no frameworks needed
make check                   # green: ruff + pyright + fast tests

$EDITOR src/frameworks.py    # TODOs 1-3: the same agent in each real library
make test-integration        # installs the heavy tree, runs the real tier
```

## What the first failure means

`test_all_three_produce_an_answer` fails because the miniatures aren't built.
Each is ~15 honest lines and captures one defining idea: `langgraph_style`
checkpoints state after each node, `TypedAgent.run` validates before answering,
`crew_style` passes context from one `Worker` to the next.

`test_durability_follows_the_measurement_not_the_reputation` fails because
`matrix.py` is empty. That file never imports a framework — it scores whatever
you measured — so you can finish it before the heavy install lands.

## The one rule of the bakeoff

**All three run the same task**: look a fact up with a tool, then answer with it.
The tempting version of this exercise gives each library the thing it is best at
— LangGraph checkpointing, Pydantic AI validating, CrewAI orchestrating roles —
and that is three demos, not a comparison. It concludes exactly what it assumed.
When the task is fixed, the differences that remain (how much glue, what you get
for free, what you still have to build) belong to the framework.

## Done when

- [ ] `make check` is green (lint, types, fast tests).
- [ ] `make test-integration` runs the shared agent in all three; every run
      reports `used_the_tool()` true — an agent that invents the fact has failed
      the task even when the sentence reads well.
- [ ] Your matrix scores all six dimensions from `Measured` rows you actually
      recorded, and you can say out loud what each number came from.
- [ ] You wrote down what `undecided()` returned and what you'd change to
      decide it. A matrix with a winner in every row is a matrix that guessed.

## Stuck?

1. Start with `matrix.py` — it's pure functions and needs no install. `winner`
   is undecided in *two* cases: several frameworks tied on the best value, or
   the whole spread sits inside `NOISE_RATIO`.
2. `langgraph_run`: `StateGraph(State)` with two nodes, `set_entry_point`, edges
   to `END`, then `.compile(checkpointer=MemorySaver())`. Pass
   `{"configurable": {"thread_id": thread}}` on `invoke`. Get `resumable` from
   `app.get_state(config)` — read it back rather than asserting it.
3. `pydantic_ai_run`: `Agent(TestModel(), deps_type=str, output_type=Answer)`
   where `Answer` is a `BaseModel`. Pass the topic as `deps`, and register a
   tool taking `RunContext[str]` with no other arguments — `TestModel` fills
   *model-chosen* arguments with throwaway strings, so a `lookup(topic: str)`
   signature makes your agent look up `"a"` and pass a naive assertion.
4. `crewai_run`: wrap the tool with `@tool("lookup")` from `crewai.tools`, give
   it to one `Agent(role=..., goal=..., backstory=..., tools=[...], llm=LLM(...))`,
   one `Task`, then `Crew(...).kickoff()`.
5. For the `spans` column, count what your tracer received; for `glue_lines`,
   count the lines of *your* code in each function, not the library's.

## The CrewAI bound (read before you debug it)

CrewAI needs **Python 3.12** and a model **on the host** — Ollama serving
`qwen3.5:9b` at `localhost:11434`.

On a newer interpreter it dies inside Chroma's Pydantic v1 shim with `unable to
infer type for attribute "chroma_server_nofile"`. That is a Python version
bound wearing a CrewAI bug's clothes, and the test skips with that message
rather than letting you chase it. A model pulled inside a Docker volume is
likewise not reachable from a host-run test.

Both skips are data. LangGraph and Pydantic AI run offline on any supported
Python; CrewAI constrains your interpreter and needs a live model to test at
all — that belongs in the observability row of your matrix.
