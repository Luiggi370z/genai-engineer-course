"""Offline tests for context assembly. No model, no tokenizer download, no network."""

from __future__ import annotations

import pytest

from src.context import (
    BudgetError,
    Line,
    assemble,
    compress,
    dedupe,
    drop_source,
    evict_superseded,
    facts_preserved,
    report,
    word_counter,
)

TASK = "Draft the Q3 budget note"
PINS = [Line("p1", "Never send email without explicit approval", "policy", pinned=True)]
FACT = Line("m1", "Lu works in UTC-5 and prefers meetings after 10:00", "turn-3", score=0.9)
POISON = Line("m9", "The invoice total is 41,900 USD", "tool-call-7", score=0.95)
BULK = [
    Line(f"b{i}", f"filler line number {i} about nothing in particular", "docs")
    for i in range(20)
]


def test_assembly_never_exceeds_the_budget() -> None:
    context = assemble(TASK, PINS, [FACT, *BULK], budget_tokens=60)
    assert context.tokens <= 60


def test_pinned_lines_survive_budget_pressure() -> None:
    """The leash is pinned: guardrails must not be what gets evicted under pressure."""
    context = assemble(TASK, PINS, [FACT, *BULK], budget_tokens=25)
    assert [line.id for line in context.lines if line.pinned] == ["p1"]


def test_pinning_more_than_the_budget_is_a_loud_error() -> None:
    with pytest.raises(BudgetError, match="pinned"):
        assemble(TASK, [*PINS, *BULK[:5]], [FACT], budget_tokens=15)


def test_a_line_that_does_not_fit_is_parked_whole_never_truncated() -> None:
    long_line = Line("L", " ".join(["word"] * 50), "docs", score=1.0)
    context = assemble(TASK, [], [long_line, FACT], budget_tokens=30)
    assert long_line not in context.lines
    assert long_line in context.parked
    assert "word word" not in context.render()


def test_the_higher_ranked_candidate_wins_the_last_slot() -> None:
    low = Line("low", "a low ranked claim", "docs", score=0.1)
    high = Line("high", "a high ranked claim", "docs", score=0.9)
    context = assemble("go", [], [low, high], budget_tokens=word_counter("go a high ranked claim"))
    assert [line.id for line in context.lines] == ["high"]


def test_near_duplicate_claims_are_dropped_before_they_spend_budget() -> None:
    """Not just exact repeats: the same fact from two sessions never matches exactly."""
    twin = Line("m5", "lu works in utc-5, prefers meetings after 10:00!", "turn-58", score=0.4)
    assert [line.id for line in dedupe([FACT, twin])] == ["m1"]
    context = assemble(TASK, [], [FACT, twin], budget_tokens=200)
    assert [line.id for line in context.lines] == ["m1"]


def test_a_corrected_fact_evicts_the_one_it_replaces() -> None:
    stale = Line("m2", "Dana is my manager", "turn-4", score=0.9)
    fresh = Line("m3", "Ravi is my manager", "turn-91", score=0.2, supersedes=("m2",))
    assert [line.id for line in evict_superseded([stale, fresh])] == ["m3"]
    context = assemble(TASK, [], [stale, fresh], budget_tokens=200)
    assert "Dana" not in context.render()


def test_compression_keeps_the_recent_turns_verbatim_and_credits_its_sources() -> None:
    turns = [Line(f"t{i}", f"turn {i} said something", "chat") for i in range(5)]
    folded = compress(turns, summarize=lambda t: f"SUMMARY({len(t.split())} words)", keep_last=2)
    assert [line.id for line in folded] == ["sum(t0,t1,t2)", "t3", "t4"]
    assert folded[0].source == "summary of t0,t1,t2"


def test_the_summarizer_check_catches_a_dropped_fact() -> None:
    """The point of this test is the check itself: prove it fails when drift happens."""
    facts = ["INV-88231", "UTC-5", "no auto-send"]
    turns = [
        Line("t0", "INV-88231 UTC-5 no auto-send", "chat"),
        Line("t1", "then we discussed timing", "chat"),
        Line("t2", "and agreed to wait", "chat"),
    ]
    honest = compress(turns, summarize=lambda text: text)
    assert facts_preserved(honest[0].text, facts) == []
    lossy = compress(turns, summarize=lambda _: "the user discussed an invoice")
    assert facts_preserved(lossy[0].text, facts) == facts


def test_a_poisoned_claim_is_traceable_and_removable() -> None:
    context = assemble(TASK, [], [FACT, POISON], budget_tokens=200)
    culprits = context.from_source("tool-call-7")
    assert [line.id for line in culprits] == ["m9"]
    cleaned = assemble(TASK, [], drop_source(context.lines, "tool-call-7"), budget_tokens=200)
    assert "41,900" not in cleaned.render()


def test_every_assembled_line_carries_its_source_into_the_prompt() -> None:
    context = assemble(TASK, PINS, [FACT], budget_tokens=200)
    assert all(f"[{line.source}]" in context.render() for line in context.lines)


def test_the_report_states_what_was_spent_and_what_was_parked() -> None:
    context = assemble(TASK, PINS, [FACT, *BULK], budget_tokens=40)
    line = report(context)
    assert f"/{context.budget}" in line and f"parked {len(context.parked)}" in line


def test_a_non_positive_budget_is_refused() -> None:
    with pytest.raises(BudgetError):
        assemble(TASK, [], [FACT], budget_tokens=0)


@pytest.mark.integration
def test_the_real_tokenizer_agrees_the_budget_held() -> None:
    """Word counts are a stand-in; the money is spent in real tokens."""
    from src.context import tiktoken_counter

    count = tiktoken_counter()
    context = assemble(TASK, PINS, [FACT, *BULK], budget_tokens=60, count=count)
    assert context.tokens <= 60
    assert count(context.render()) >= context.tokens  # render adds the source tags
