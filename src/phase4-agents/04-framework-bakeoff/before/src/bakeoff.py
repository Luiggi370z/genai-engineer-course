"""TODO: implement the SAME agent three ways to feel the trade-offs.

- langgraph_style(query, tool): a mini state machine with a checkpoint after each
  node (durability is the idea).
- TypedAgent: validate the query up front, then answer (type-safety is the idea).
- crew_style(query, workers): role-based workers each take a turn passing context
  along (fast multi-role prototyping is the idea).

These miniatures are the FAST tier — for feeling the shape of each idea offline.
The real tier is tests/test_integration.py: the same three ideas proven in the
actual libraries (LangGraph, Pydantic AI, CrewAI) via `make test-integration`.

Then write a one-paragraph verdict in README — from the real tier, not the
miniatures: which fits which job, and why. Reference: ../after/src/bakeoff.py.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

Tool = Callable[[str], str]


def langgraph_style(query: str, answer_tool: Tool) -> str:
    raise NotImplementedError  # TODO 1


@dataclass
class TypedAgent:
    answer_tool: Tool

    def run(self, query: str) -> str:
        raise NotImplementedError  # TODO 2


@dataclass
class Worker:
    role: str
    fn: Callable[[str], str]


def crew_style(query: str, workers: list[Worker]) -> str:
    raise NotImplementedError  # TODO 3
