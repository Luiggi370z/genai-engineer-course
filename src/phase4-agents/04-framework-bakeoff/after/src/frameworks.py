"""The SAME tool-using agent, in three real libraries.

`bakeoff.py` holds ~15-line miniatures that capture each defining idea. This file
is the tier that produces the verdict: LangGraph, Pydantic AI and CrewAI, each
running **the same agent on the same task**, returning **the same result shape**.

## Why the task has to be identical

The tempting version of a bakeoff shows each library doing what it is best at —
LangGraph checkpointing, Pydantic AI validating, CrewAI orchestrating roles. That
is three demos, not a comparison, and it concludes exactly what it assumed. You
cannot learn from it that LangGraph costs more glue, because the LangGraph
example was never asked to do the thing Pydantic AI did in one line.

So all three get one task: **look a fact up with a tool, then answer with it.**
One tool, one topic, one sentence out. It is deliberately unremarkable, because
the differences it exposes — how much wiring, what you get for free, what you
still have to build — are the differences that show up in a real service.

## Why they return the same shape

`Run` is what makes the measurements comparable. `tool_calls` proves the tool
actually ran (an agent that hallucinates the fact and skips the tool "passes" a
naive assertion), and `resumable` reports whether the framework left state a
second invocation could pick up — measured by asking, not by reading the docs.

Imports are inside the functions. The libraries are a heavy tree in the
`integration` group, and this module has to import cleanly in the fast tier so
`matrix.py` can be tested without them.

Note the missing `from __future__ import annotations`, which the rest of this
course uses everywhere. It has to stay out: it turns annotations into strings
that Pydantic AI later resolves against *module* globals, where a
function-local `RunContext` import does not exist. Lazy imports and postponed
annotations do not compose, and the failure is a `NameError` from inside the
library that says nothing about either cause.
"""
from dataclasses import dataclass, field

#: The one fact the tool knows. Tiny on purpose: the interesting part is whether
#: the agent went and got it, not whether the model knows about vector stores.
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
    that looks identical to one that looked the fact up. Counting the calls is
    the only honest check, and it is the same check in all three frameworks.
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
    #: Measured by asking it, not by trusting the README.
    resumable: bool

    def used_the_tool(self) -> bool:
        return bool(self.tool_calls)


# --- LangGraph -----------------------------------------------------------------


def langgraph_run(topic: str = TOPIC, thread: str = "bakeoff") -> Run:
    """A two-node graph — look up, then answer — compiled with a checkpointer.

    The glue is the cost and the durability is the payoff. You declare a state
    schema, add nodes, wire edges, compile, and pass a `thread_id` on every
    invoke. In exchange, the run's state is addressable afterwards: `get_state`
    returns it, and a second invocation on the same thread continues rather than
    starts over. Nothing else here offers that without a database.
    """
    from typing import TypedDict

    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.graph import END, StateGraph

    recorder = Recorder()

    class State(TypedDict, total=False):
        topic: str
        fact: str
        answer: str

    def look_up(state: State) -> dict:
        return {"fact": recorder.lookup(state.get("topic", ""))}

    def answer(state: State) -> dict:
        return {"answer": f"{state.get('topic', '')}: {state.get('fact', '')}"}

    graph = StateGraph(State)
    graph.add_node("look_up", look_up)
    graph.add_node("answer", answer)
    graph.set_entry_point("look_up")
    graph.add_edge("look_up", "answer")
    graph.add_edge("answer", END)
    app = graph.compile(checkpointer=MemorySaver())

    config = {"configurable": {"thread_id": thread}}
    out = app.invoke({"topic": topic}, config)
    # Not "LangGraph has checkpointing" — a measurement. The state is there, or
    # the claim in the matrix is not ours to make.
    resumable = bool(app.get_state(config).values.get("answer"))
    return Run("langgraph", out.get("answer", ""), tuple(recorder.calls), resumable)


# --- Pydantic AI ----------------------------------------------------------------


def pydantic_ai_run(topic: str = TOPIC) -> Run:
    """One agent, one registered tool, one typed output. No graph.

    The contrast with LangGraph is the whole lesson: the tool is a decorated
    function, the output contract is a `BaseModel`, and there is no state schema
    to declare because there is no persisted state. A malformed reply fails at
    the boundary instead of flowing downstream — and nothing survives the
    process, which is the trade you are making.

    `TestModel` drives it offline: it calls every registered tool once and
    synthesises a conforming output, so the wiring is under test without a model
    provider, a key or a bill.

    The topic arrives through `deps`, not as a tool argument, and that detail is
    load-bearing twice over. It is the framework's own idiom — values the caller
    controls are dependencies, values the model chooses are arguments — and it
    is what makes an offline test mean anything: `TestModel` fills model-chosen
    arguments with throwaway strings, so a `lookup(topic: str)` signature would
    have this agent dutifully looking up `"a"` and passing a naive assertion.
    """
    from pydantic import BaseModel
    from pydantic_ai import Agent, RunContext
    from pydantic_ai.models.test import TestModel

    recorder = Recorder()

    class Answer(BaseModel):
        topic: str
        fact: str

    agent = Agent(TestModel(), deps_type=str, output_type=Answer)

    @agent.tool
    def lookup(ctx: RunContext[str]) -> str:
        """Look up one fact about the topic under discussion."""
        return recorder.lookup(ctx.deps)

    result = agent.run_sync("Look up the topic and report the fact.", deps=topic)
    answer = f"{result.output.topic}: {result.output.fact}"
    # Nothing to ask: there is no store to interrogate. Reporting False is the
    # honest measurement, and it is exactly the row that decides an architecture.
    return Run("pydantic-ai", answer, tuple(recorder.calls), resumable=False)


# --- CrewAI ----------------------------------------------------------------------


def crewai_run(topic: str = TOPIC, model: str = "ollama/qwen3.5:9b") -> Run:
    """One agent, one tool, one task — the smallest crew that does the job.

    CrewAI is built around several roles collaborating, so the shared task makes
    it look like ceremony, and that is a fair finding rather than an unfair test:
    a single tool-using step really does cost more here. The lesson is to notice
    when your problem is the shape CrewAI is for, and when you are paying for an
    orchestration you do not need.

    Needs a real model. Unlike the other two there is no offline test double, and
    that absence belongs in the observability and cost rows of the matrix.
    """
    from crewai import LLM, Agent, Crew, Task
    from crewai.tools import tool

    recorder = Recorder()

    @tool("lookup")
    def lookup(topic: str) -> str:
        """Look up one fact about the topic."""
        return recorder.lookup(topic)

    researcher = Agent(
        role="researcher",
        goal="Report the looked-up fact about the topic, verbatim.",
        backstory="Terse. Uses the lookup tool and quotes what it returns.",
        tools=[lookup],
        llm=LLM(model=model, base_url="http://localhost:11434"),
    )
    task = Task(
        description=f"Use the lookup tool on '{topic}' and report the fact it returns.",
        expected_output="One sentence: the fact.",
        agent=researcher,
    )
    result = Crew(agents=[researcher], tasks=[task]).kickoff()
    return Run("crewai", str(result), tuple(recorder.calls), resumable=False)
