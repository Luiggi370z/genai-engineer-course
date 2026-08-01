"""Trajectory metrics run in the fast tier — these tests ARE the fast tier."""
from __future__ import annotations

from src.trajectory import (
    ToolCall,
    argument_accuracy,
    goal_completion,
    order_respected,
    score_trajectory,
    step_economy,
    tool_choice_f1,
    unapproved_gated_calls,
)

REFERENCE = [
    ToolCall("list_events", {"day": "tomorrow"}),
    ToolCall("send_email", {"to": "alice"}),
]


def test_perfect_trajectory_scores_one_everywhere():
    scores = score_trajectory(REFERENCE, REFERENCE, gated={"send_email"}, approvals={"send_email"})
    assert all(value == 1.0 for value in scores.values()), scores


def test_a_wrong_tool_drops_choice_f1():
    actual = [ToolCall("delete_event", {"id": "7"}), ToolCall("send_email", {"to": "alice"})]
    assert tool_choice_f1(actual, REFERENCE) == 0.5
    assert tool_choice_f1([], REFERENCE) == 0.0
    assert tool_choice_f1([], []) == 1.0


def test_right_tool_wrong_arguments_is_caught_structurally():
    actual = [ToolCall("list_events", {"day": "tomorrow"}), ToolCall("send_email", {"to": "bob"})]
    assert tool_choice_f1(actual, REFERENCE) == 1.0  # names are fine…
    assert argument_accuracy(actual, REFERENCE) == 0.5  # …the args are not


def test_order_is_checked_separately_from_choice():
    reversed_calls = list(reversed(REFERENCE))
    assert tool_choice_f1(reversed_calls, REFERENCE) == 1.0
    assert not order_respected(reversed_calls, REFERENCE)
    # extra calls in between do not break sequencing
    padded = [REFERENCE[0], ToolCall("read_note", {}), REFERENCE[1]]
    assert order_respected(padded, REFERENCE)


def test_a_gated_tool_without_approval_is_named():
    actual = [ToolCall("send_email", {"to": "alice"})]
    assert unapproved_gated_calls(actual, gated={"send_email"}) == ["send_email"]
    assert unapproved_gated_calls(actual, gated={"send_email"}, approvals={"send_email"}) == []


def test_burning_extra_steps_degrades_economy():
    padded = REFERENCE + [ToolCall("list_events", {"day": "today"})] * 4
    assert step_economy(padded, REFERENCE) == round(2 / 6, 3)
    assert step_economy(REFERENCE, REFERENCE) == 1.0


def test_goal_completion_is_a_structural_check_on_the_outcome():
    outcome = {"draft_exists": True, "recipient": "alice", "sent": False}
    assert goal_completion(outcome, {"draft_exists": True, "recipient": "alice"}) == 1.0
    assert goal_completion(outcome, {"draft_exists": True, "recipient": "bob"}) == 0.5
    assert goal_completion({}, {}) == 1.0
