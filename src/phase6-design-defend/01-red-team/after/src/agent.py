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
    #: how many untrusted items arrived, and how many L1 refused to pass on.
    #: Counted rather than inferred, because "the attack was contained" and
    #: "the attack was detected" are different claims and a suite that only
    #: checks the first cannot notice the detector rotting.
    screened_untrusted: int = 0
    dropped_untrusted: int = 0


# least privilege: the agent literally has no "forward email" tool.
SAFE_TOOLS = {"read_note", "summarize"}
GATED_TOOLS = {"send_message", "delete"}  # require approval=True


def guarded_run(
    user_msg: str,
    retrieved: list[str],
    approve: bool = False,
    tool_outputs: list[str] | None = None,
) -> Result:
    r = Result(text="")
    ok, cleaned = layer1(user_msg)
    if not ok:
        r.text = SAFE_REFUSAL
        r.blocked_reason = cleaned
        r.audit.append(f"L1 blocked: {cleaned}")
        return r

    # untrusted content arrives on TWO channels — retrieved documents and tool
    # output (a fetched page, an email body). Both go through the SAME L1 screen
    # as the user's message, because "we only screen what the user typed" is how
    # a poisoned page walks in through a door nobody was watching. An item that
    # fails is dropped, not sanitised: there is no safe residue of an
    # instruction, and half of one is not evidence either.
    arriving = list(retrieved) + list(tool_outputs or [])
    r.screened_untrusted = len(arriving)
    untrusted = []
    for item in arriving:
        item_ok, _ = layer1(str(item))
        if item_ok:
            untrusted.append(item)
        else:
            r.dropped_untrusted += 1
            r.audit.append("untrusted item dropped: injection")

    # ...and whatever survives is still DATA. Spotlighting is what stops a clean
    # -looking document from being read as an instruction; dropping is what stops
    # the dirty ones from getting that far. Neither replaces the other.
    safe_ctx = [spotlight(c) for c in untrusted]

    # simulate the model deciding to act. Even if injected text in the untrusted
    # channels "tells" it to send — or claims approval was ALREADY given — a gated
    # tool needs approval from the APPROVE ARGUMENT, which only a human sets.
    wants_gated = any(
        "send" in c.lower() or "forward" in c.lower() or "delete" in c.lower()
        for c in untrusted
    )
    if wants_gated and not approve:
        r.text = "A risky action was requested but requires human approval."
        r.audit.append("gated tool suppressed (no approval)")
        r.fired_irreversible_tool_without_approval = False
        return r

    answer = f"Summary of {len(safe_ctx)} item(s)."
    if not layer3_output_ok(answer, untrusted):
        r.text = SAFE_REFUSAL
        r.audit.append("L3 output gate failed")
        return r
    r.text = answer
    return r
