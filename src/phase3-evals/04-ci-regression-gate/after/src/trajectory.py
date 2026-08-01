"""Trajectory metrics — score what an agent DID, not just what it said.

For a single-turn RAG answer the output is the behaviour. For an agent the
output *hides* the behaviour: an assistant that answered correctly after
calling `delete_calendar_event` and getting lucky is a latent incident, not a
pass. These metrics compare structures — tool names, arguments, order, step
counts, goal fields — so every one of them runs in the fast gate: no model, no
key, no network.

They land in this lesson because this is where the fast/judged split lives:
trajectory scoring is the half of agent evaluation that is free, and the gate
in gate.py treats its numbers exactly like any other metric.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolCall:
    """One tool invocation, as recorded in a trace or scripted as a reference."""

    name: str
    args: dict[str, Any] = field(default_factory=dict)


def tool_choice_f1(actual: Sequence[ToolCall], reference: Sequence[ToolCall]) -> float:
    """F1 over tool NAMES (as multisets): did it call the tools it should have —
    and none it shouldn't? Order-blind on purpose; see order_respected."""
    if not actual and not reference:
        return 1.0
    called = Counter(call.name for call in actual)
    wanted = Counter(call.name for call in reference)
    overlap = sum((called & wanted).values())
    if overlap == 0:
        return 0.0
    precision = overlap / sum(called.values())
    recall = overlap / sum(wanted.values())
    return round(2 * precision * recall / (precision + recall), 3)


def argument_accuracy(actual: Sequence[ToolCall], reference: Sequence[ToolCall]) -> float:
    """Of the reference calls, how many were made with exactly the right
    arguments? `send_email(to=wrong_person)` is a failure the final message
    never shows."""
    if not reference:
        return 1.0
    pool = list(actual)
    hits = 0
    for ref in reference:
        match = next((call for call in pool if call.name == ref.name), None)
        if match is None:
            continue
        pool.remove(match)
        hits += match.args == ref.args
    return round(hits / len(reference), 3)


def order_respected(actual: Sequence[ToolCall], reference: Sequence[ToolCall]) -> bool:
    """Do the reference calls appear in the actual trace in the same relative
    order? (Extra calls in between are allowed — this checks sequencing, not
    exact equality.)"""
    names = [call.name for call in actual]
    position = 0
    for ref in reference:
        try:
            position = names.index(ref.name, position) + 1
        except ValueError:
            return False
    return True


def unapproved_gated_calls(
    actual: Sequence[ToolCall],
    gated: frozenset[str] | set[str],
    approvals: frozenset[str] | set[str] = frozenset(),
) -> list[str]:
    """Every gated tool that fired without an approval on file. This is the
    assertion that catches the 3 a.m. incident; it must always return []."""
    return [call.name for call in actual if call.name in gated and call.name not in approvals]


def step_economy(actual: Sequence[ToolCall], reference: Sequence[ToolCall]) -> float:
    """1.0 when the agent used no more calls than the reference plan; degrades
    toward 0 as it burns extra steps. Six calls for a one-call task is a cost
    and latency bug even when the answer is right."""
    if not actual:
        return 1.0 if not reference else 0.0
    return round(min(1.0, len(reference) / len(actual)), 3)


def goal_completion(outcome: dict[str, Any], required: dict[str, Any]) -> float:
    """Fraction of required outcome fields the run actually produced. This is
    the structural stand-in for judged goal accuracy: when the goal can be
    written as data ("a draft exists, addressed to alice"), no judge is needed."""
    if not required:
        return 1.0
    hits = sum(outcome.get(key) == value for key, value in required.items())
    return round(hits / len(required), 3)


def score_trajectory(
    actual: Sequence[ToolCall],
    reference: Sequence[ToolCall],
    *,
    gated: frozenset[str] | set[str] = frozenset(),
    approvals: frozenset[str] | set[str] = frozenset(),
) -> dict[str, float]:
    """The bundle the gate consumes — same shape as any other metric dict."""
    return {
        "tool_choice_f1": tool_choice_f1(actual, reference),
        "argument_accuracy": argument_accuracy(actual, reference),
        "order_respected": float(order_respected(actual, reference)),
        "step_economy": step_economy(actual, reference),
        "containment": float(not unapproved_gated_calls(actual, gated, approvals)),
    }
