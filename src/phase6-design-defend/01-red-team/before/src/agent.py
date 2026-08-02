"""TODO: harden this naive agent so no landed injection can fire a gated tool.

Wire in guardrails.layer1 (on user input AND on every untrusted item), spotlight
whatever survives, keep gated tools behind approval, and add the L3 output gate.
Tool output (`tool_outputs`) is the SECOND untrusted channel — a fetched page or
email body gets exactly the retrieved-document treatment, and content on either
channel can never grant approval (only the `approve` argument, set by a human,
can). The redteam tests define "contained".

Screen both channels, do not merely spotlight them. Spotlighting stops a
clean-looking document from being read as an instruction; screening stops the
dirty ones from getting that far. Neither replaces the other, and an item that
fails is DROPPED rather than sanitised — there is no safe residue of an
instruction, and half of one is not evidence either.

Count what you drop. "Nothing bad happened" is the weakest possible pass, and it
is exactly what a detector that has stopped working still produces, because
containment holds the line whether or not the screen ever fired.

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
    #: how many untrusted items arrived, and how many L1 refused to pass on
    screened_untrusted: int = 0
    dropped_untrusted: int = 0


def guarded_run(
    user_msg: str,
    retrieved: list[str],
    approve: bool = False,
    tool_outputs: list[str] | None = None,
) -> Result:
    raise NotImplementedError  # TODO: contain it, and count what you dropped
