"""Workshop 2 layer — the agent loop with HITL, built on the Phase-3 pattern.

The 'brain' (decide) is injected so tests are deterministic/offline. Gated tools
never fire without approval; the loop has a hard step cap.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from assistant.tools import REGISTRY, Tool


@dataclass
class Step:
    tool: str
    args: dict[str, Any]
    is_final: bool = False
    answer: str = ""


@dataclass
class Pending:
    tool: str
    args: dict[str, Any]


@dataclass
class AgentResult:
    text: str = ""
    pending: Pending | None = None
    audit: list[str] = field(default_factory=list)
    fired_irreversible_tool_without_approval: bool = False


Decider = Callable[[str, list[tuple[Step, Any]]], Step]


def run(goal: str, decide: Decider, approvals: dict[str, bool] | None = None,
        registry: dict[str, Tool] | None = None, max_steps: int = 8) -> AgentResult:
    registry = registry or REGISTRY
    approvals = approvals or {}
    result = AgentResult()
    state: list[tuple[Step, Any]] = []
    for _ in range(max_steps):
        step = decide(goal, state)
        if step.is_final:
            result.text = step.answer
            return result
        tool = registry.get(step.tool)
        if tool is None:
            state.append((step, {"error": f"unknown tool {step.tool!r}"}))
            continue
        if tool.requires_approval and not approvals.get(step.tool, False):
            # pause instead of firing — HITL containment
            result.pending = Pending(step.tool, step.args)
            result.audit.append(f"paused for approval: {step.tool}")
            return result
        out = tool.fn(**step.args)
        state.append((step, out))
    result.text = "stopped: max_steps"
    return result
