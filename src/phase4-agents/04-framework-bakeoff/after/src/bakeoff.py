"""The SAME agent, three ways — so you can feel the trade-offs.

Two tiers, honestly labelled:

**Fast tier (this file).** Each "framework" is a hand-written *miniature* that
captures its defining idea in ~15 lines, so the comparison runs offline with no
heavy installs:
  - langgraph_style: a state machine with nodes + a checkpoint dict (durability)
  - pydantic_style: a typed agent where args are validated models (safety)
  - crew_style: role-based workers that each take a turn (fast multi-role)

**Real tier (tests/test_integration.py).** The same three ideas proven in the
actual libraries — LangGraph's StateGraph + checkpointer, Pydantic AI's typed
outputs, CrewAI's role/task orchestration — via `make test-integration`.

The miniatures are for feeling the shape of each idea; the verdict you write in
the README must come from the real tier.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

Tool = Callable[[str], str]


# ---- LangGraph-style: state machine + checkpoint (durability is the big idea) ----
@dataclass
class Graph:
    nodes: dict[str, Callable[[dict], dict]] = field(default_factory=dict)
    edges: dict[str, str] = field(default_factory=dict)
    checkpoint: dict = field(default_factory=dict)

    def run(self, start: str, state: dict) -> dict:
        node = start
        while node != "END":
            state = self.nodes[node](state)
            self.checkpoint = dict(state)  # save point after every node
            node = self.edges[node]
        return state


def langgraph_style(query: str, answer_tool: Tool) -> str:
    g = Graph()
    g.nodes["work"] = lambda s: {**s, "result": answer_tool(s["q"])}
    g.edges["work"] = "END"
    return g.run("work", {"q": query})["result"]


# ---- Pydantic-style: typed, validated, minimal ceremony (safety is the big idea) --
@dataclass
class TypedAgent:
    answer_tool: Tool

    def run(self, query: str) -> str:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")  # validation up front
        return self.answer_tool(query)


# ---- CrewAI-style: role-based workers collaborating (speed of prototyping) --------
@dataclass
class Worker:
    role: str
    fn: Callable[[str], str]


def crew_style(query: str, workers: list[Worker]) -> str:
    ctx = query
    for w in workers:  # each role takes a turn, passing context along
        ctx = w.fn(ctx)
    return ctx


def demo_answer(q: str) -> str:
    return f"answer to: {q}"


if __name__ == "__main__":
    print(langgraph_style("hi", demo_answer))
    print(TypedAgent(demo_answer).run("hi"))
    print(crew_style("hi", [Worker("researcher", lambda x: x + " [researched]"),
                            Worker("writer", demo_answer)]))
