"""A tiny guarded agent: least-privilege tools + HITL, wrapped by the guardrails.

Demonstrates containment — even if an injection slips past L1, the irreversible
tool still can't fire without human approval.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.guardrails import layer1, layer3_output_ok, spotlight

SAFE_REFUSAL = "I can't help with that request."


@dataclass
class Result:
    text: str
    fired_irreversible_tool_without_approval: bool = False
    leaked_pii: bool = False
    blocked_reason: str = ""
    audit: list[str] = field(default_factory=list)


# least privilege: the agent literally has no "forward email" tool.
SAFE_TOOLS = {"read_note", "summarize"}
GATED_TOOLS = {"send_message", "delete"}  # require approval=True


def guarded_run(user_msg: str, retrieved: list[str], approve: bool = False) -> Result:
    r = Result(text="")
    ok, cleaned = layer1(user_msg)
    if not ok:
        r.text = SAFE_REFUSAL
        r.blocked_reason = cleaned
        r.audit.append(f"L1 blocked: {cleaned}")
        return r

    # untrusted retrieved content is spotlighted, never trusted as instructions
    safe_ctx = [spotlight(c) for c in retrieved]

    # simulate the model deciding to act. Even if injected text in `retrieved`
    # "tells" it to send a message, a gated tool needs approval — containment.
    wants_gated = any("send" in c.lower() or "forward" in c.lower() for c in retrieved)
    if wants_gated and not approve:
        r.text = "A risky action was requested but requires human approval."
        r.audit.append("gated tool suppressed (no approval)")
        r.fired_irreversible_tool_without_approval = False
        return r

    answer = f"Summary of {len(safe_ctx)} item(s)."
    if not layer3_output_ok(answer, retrieved):
        r.text = SAFE_REFUSAL
        r.audit.append("L3 output gate failed")
        return r
    r.text = answer
    return r
