"""TODO: run the SAME tool-using agent in three real libraries.

`bakeoff.py` is the miniatures — the shape of each idea in ~15 offline lines.
This file is the tier your verdict has to come from, and it is the one you own:
LangGraph, Pydantic AI and CrewAI, each running **the same agent on the same
task**, each returning **the same `Run` shape**.

## Why the task has to be identical

The tempting version shows each library doing what it is best at, and concludes
exactly what it assumed. You cannot learn that LangGraph costs more glue from an
example where LangGraph was never asked to do the one-line thing.

So all three get one task: **look a fact up with a tool, then answer with it.**
Unremarkable on purpose — the differences it exposes (how much wiring, what you
get for free, what you still have to build) are the ones that show up in a real
service.

## The TODOs

1. `langgraph_run` — a two-node graph (look up → answer) compiled with a
   `MemorySaver`, invoked with a `thread_id`, and then *asked* whether its state
   survived. Do not hardcode `resumable=True`; read it back with `get_state`.
2. `pydantic_ai_run` — one `Agent` with a registered tool and a `BaseModel`
   output type. Drive it with `TestModel` so it runs offline.
3. `crewai_run` — one `Agent` with the same tool, one `Task`, one `Crew`.

Run them with `make test-integration` (needs the opt-in install; the CrewAI test
also needs Ollama). Then feed what you measured into `matrix.py`.

Imports go INSIDE the functions: the libraries live in the `integration`
dependency group, and this module must import cleanly in the fast tier so
`matrix.py` is testable without them.

Do NOT add `from __future__ import annotations` here, even though the rest of
the course uses it. It turns annotations into strings that Pydantic AI resolves
against *module* globals, where a function-local `RunContext` import does not
exist — lazy imports and postponed annotations do not compose, and the failure
is a `NameError` from inside the library that names neither cause.

Reference: ../after/src/frameworks.py.
"""
from dataclasses import dataclass, field

#: The one fact the tool knows. Tiny on purpose: the interesting part is whether
#: the agent went and got it.
FACTS = {
    "checkpointing": "A checkpoint lets a run resume from its last completed step.",
    "quantization": "Quantization trades a little accuracy for much less memory.",
}
UNKNOWN = "No fact on file."
TOPIC = "checkpointing"


@dataclass
class Recorder:
    """The tool, plus a record of every call to it.

    The record is the point. "Did the agent use the tool?" is not answerable from
    the final string — a model that invents a plausible sentence produces output
    that looks identical. Counting the calls is the only honest check, and it is
    the same check in all three frameworks.
    """

    calls: list[str] = field(default_factory=list)

    def lookup(self, topic: str) -> str:
        """Look up one fact about `topic`."""
        self.calls.append(topic)
        return FACTS.get(topic.strip().lower(), UNKNOWN)


@dataclass(frozen=True)
class Run:
    """One framework's answer to the shared task, in a shape the others share."""

    framework: str
    answer: str
    tool_calls: tuple[str, ...]
    #: Did the framework leave state behind that a second invocation can read?
    #: Measure it. Do not quote the README.
    resumable: bool

    def used_the_tool(self) -> bool:
        return bool(self.tool_calls)


def langgraph_run(topic: str = TOPIC, thread: str = "bakeoff") -> Run:
    raise NotImplementedError  # TODO 1


def pydantic_ai_run(topic: str = TOPIC) -> Run:
    raise NotImplementedError  # TODO 2


def crewai_run(topic: str = TOPIC, model: str = "ollama/qwen3.5:9b") -> Run:
    raise NotImplementedError  # TODO 3
