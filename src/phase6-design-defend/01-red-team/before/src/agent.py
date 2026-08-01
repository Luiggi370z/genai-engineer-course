"""TODO: harden this naive agent so no landed injection can fire a gated tool.

Wire in guardrails.layer1 (on user input AND treat retrieved docs as untrusted),
spotlight the retrieved content, keep gated tools behind approval, and add the
L3 output gate. The redteam tests define "contained".

Reference: ../after/src/agent.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Result:
    text: str
    fired_irreversible_tool_without_approval: bool = False
    leaked_pii: bool = False
    blocked_reason: str = ""
    audit: list[str] = field(default_factory=list)


def guarded_run(user_msg: str, retrieved: list[str], approve: bool = False) -> Result:
    raise NotImplementedError  # TODO: contain it
