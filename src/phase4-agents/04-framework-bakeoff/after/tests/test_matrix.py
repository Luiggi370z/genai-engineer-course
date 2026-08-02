"""The matrix has to refuse to pick a winner more often than it picks one.

These run offline: the scoring is pure, so it is testable without installing a
single framework. What is under test is the honesty of the scoring, not the
frameworks — a matrix that always finds a winner is the bug.
"""
import pytest

from src.matrix import (
    DIMENSIONS,
    UNDECIDED,
    MatrixError,
    Measured,
    render,
    undecided,
    value,
    winner,
)


def _rows() -> list[Measured]:
    return [
        Measured("langgraph", resumable=True, recovered=True, glue_lines=24, spans=6,
                 p50_ms=40.0, tokens=0),
        Measured("pydantic-ai", resumable=False, recovered=False, glue_lines=9, spans=3,
                 p50_ms=12.0, tokens=0),
    ]


def test_durability_follows_the_measurement_not_the_reputation():
    """Only the run that proved it can resume wins the row."""
    assert winner(_rows(), "durability") == "langgraph"
    assert winner(_rows(), "complexity") == "pydantic-ai"


def test_a_tie_is_reported_as_undecided_not_broken_arbitrarily():
    """Both spent zero tokens, so 'cost' says nothing — and must admit it."""
    assert winner(_rows(), "cost") == UNDECIDED
    assert "cost" in undecided(_rows())


def test_differences_inside_the_noise_floor_do_not_crown_a_winner():
    """41ms vs 40ms is measurement noise. A matrix that calls that a win is
    laundering noise into an architectural decision."""
    rows = [
        Measured("a", False, False, 10, 3, 40.0, 100),
        Measured("b", False, False, 10, 3, 41.0, 100),
    ]
    assert winner(rows, "latency") == UNDECIDED


def test_a_difference_beyond_the_noise_floor_does():
    rows = [
        Measured("a", False, False, 10, 3, 40.0, 100),
        Measured("b", False, False, 10, 3, 400.0, 100),
    ]
    assert winner(rows, "latency") == "a"


def test_every_dimension_is_scored_and_none_is_silently_dropped():
    table = render(_rows())
    for dimension in DIMENSIONS:
        assert dimension in table
    assert len(DIMENSIONS) == 6


def test_the_table_keeps_the_measurement_beside_the_verdict():
    """A verdict without its number is prose wearing a table's clothes."""
    table = render(_rows())
    assert "24" in table and "9" in table


def test_counts_render_as_counts_and_only_booleans_render_as_yes_no():
    """One span is `1`, not `yes`; zero tokens is `0`, not `no`. The bug this
    pins made a matrix that reads plausibly and reports the wrong thing."""
    rows = [
        Measured("a", resumable=True, recovered=False, glue_lines=10, spans=1,
                 p50_ms=40.0, tokens=0),
        Measured("b", resumable=False, recovered=False, glue_lines=30, spans=9,
                 p50_ms=90.0, tokens=500),
    ]
    table = render(rows)
    durability = next(line for line in table.splitlines() if line.startswith("| durability"))
    observability = next(line for line in table.splitlines() if line.startswith("| observability"))
    assert "yes" in durability and "no" in durability
    assert "| 1 |" in observability and "yes" not in observability


def test_scoring_nothing_raises_rather_than_inventing_a_verdict():
    with pytest.raises(MatrixError):
        winner([], "latency")
    with pytest.raises(MatrixError):
        render([])
    with pytest.raises(MatrixError):
        value(_rows()[0], "developer-happiness")
