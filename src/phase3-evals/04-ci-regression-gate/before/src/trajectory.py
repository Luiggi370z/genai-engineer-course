"""TODO: trajectory metrics — score what an agent DID, not just what it said.

An agent's final message hides its behaviour: the right answer after an
unapproved `delete_calendar_event` is a latent incident, not a pass. Every
metric here compares STRUCTURES (names, args, order, counts, fields), so all
of them belong in the fast gate: no model, no key, no network.

Fill the TODOs. The tests in tests/test_trajectory.py define the exact shapes.
Reference: ../after/src/trajectory.py.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolCall:
    """One tool invocation, as recorded in a trace or scripted as a reference."""

    name: str
    args: dict[str, Any] = field(default_factory=dict)


def tool_choice_f1(actual: Sequence[ToolCall], reference: Sequence[ToolCall]) -> float:
    """TODO 1: F1 over tool NAMES as multisets (collections.Counter and its `&`
    do the heavy lifting). Both empty -> 1.0; no overlap -> 0.0; round to 3."""
    raise NotImplementedError


def argument_accuracy(actual: Sequence[ToolCall], reference: Sequence[ToolCall]) -> float:
    """TODO 2: of the reference calls, how many were made with exactly the right
    args? Pair each reference call with one unclaimed actual call of the same
    name. No reference calls -> 1.0; round to 3."""
    raise NotImplementedError


def order_respected(actual: Sequence[ToolCall], reference: Sequence[ToolCall]) -> bool:
    """TODO 3: do the reference names appear in actual in the same relative
    order? Extra calls in between are fine — check sequencing, not equality."""
    raise NotImplementedError


def unapproved_gated_calls(
    actual: Sequence[ToolCall],
    gated: frozenset[str] | set[str],
    approvals: frozenset[str] | set[str] = frozenset(),
) -> list[str]:
    """TODO 4: every gated tool that fired without an approval on file. The
    assertion that catches the 3 a.m. incident — it must always return []."""
    raise NotImplementedError


def step_economy(actual: Sequence[ToolCall], reference: Sequence[ToolCall]) -> float:
    """TODO 5: 1.0 when the agent used no more calls than the reference plan,
    degrading toward 0 as it burns extra steps (len(reference)/len(actual),
    capped at 1.0). Empty actual: 1.0 if reference is empty too, else 0.0."""
    raise NotImplementedError


def goal_completion(outcome: dict[str, Any], required: dict[str, Any]) -> float:
    """TODO 6: fraction of required outcome fields the run produced (exact
    equality per key). Nothing required -> 1.0; round to 3."""
    raise NotImplementedError


def score_trajectory(
    actual: Sequence[ToolCall],
    reference: Sequence[ToolCall],
    *,
    gated: frozenset[str] | set[str] = frozenset(),
    approvals: frozenset[str] | set[str] = frozenset(),
) -> dict[str, float]:
    """TODO 7: bundle the five metrics into one dict the gate can consume —
    keys: tool_choice_f1, argument_accuracy, order_respected, step_economy,
    containment (1.0 when unapproved_gated_calls is empty)."""
    raise NotImplementedError
