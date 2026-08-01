"""Workshop 2 layer — the agent loop with HITL, built on the Phase-3 pattern.

The 'brain' (decide) is injected so tests are deterministic/offline. Gated tools
never fire without approval; the loop has a hard step cap.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from assistant.tools import Tool


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
    raise NotImplementedError  # TODO
