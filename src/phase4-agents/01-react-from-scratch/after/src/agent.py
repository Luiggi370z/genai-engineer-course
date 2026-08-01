"""The agent loop, from scratch — reason, act, observe, with the leash in code.

The `decide` function (the model's brain) is injected so this runs offline and
deterministically in tests. In real life `decide` calls your Phase-1 client and
parses a tool request or a final answer out of the response.
"""
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Decision:
    is_final: bool
    answer: str = ""
    tool: str = ""
    args: dict[str, Any] = field(default_factory=dict)


Tool = Callable[..., Any]
Decider = Callable[[str, list[tuple[Decision, Any]]], Decision]


def run_agent(
    goal: str,
    tools: dict[str, Tool],
    decide: Decider,
    max_steps: int = 8,
    deadline_s: float = 60.0,
) -> str:
    """Loop until the model says it's done — or a HARD cap stops it. Rule #1."""
    state: list[tuple[Decision, Any]] = []
    start = time.monotonic()
    for _ in range(max_steps):  # hard cap: physics, not a prompt request
        if time.monotonic() - start > deadline_s:
            return "FAILED: timeout"
        d = decide(goal, state)
        if d.is_final:
            return d.answer
        if d.tool not in tools:
            state.append((d, {"error": f"unknown tool {d.tool!r}"}))
            continue
        try:
            result = tools[d.tool](**d.args)  # YOUR code runs it
        except Exception as e:  # noqa: BLE001 — errors are data the agent can react to
            result = {"error": str(e)}
        state.append((d, result))
    return "FAILED: max_steps_exceeded"  # degrade gracefully, never hang


# --- example tools ---
def calculator(expression: str) -> float:
    """Evaluate a simple arithmetic expression."""
    return float(eval(expression, {"__builtins__": {}}, {}))  # noqa: S307 — sandboxed dict


def search(query: str) -> str:
    """Pretend web search."""
    return f"top result for {query!r}"
