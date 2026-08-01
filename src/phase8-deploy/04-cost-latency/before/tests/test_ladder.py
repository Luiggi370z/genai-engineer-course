"""The ladder as a whole: does the order actually hold, and does the gate bite?"""
from __future__ import annotations

from collections.abc import Sequence

import pytest

from src.cache import ExactCache, SemanticCache
from src.ladder import Ladder, Report, budget_gate, percentile, report
from src.router import Tier

SPACE: dict[str, Sequence[float]] = {
    "what is the refund policy": (1.0, 0.0),
    "how do refunds work": (0.99, 0.0),
    "who is our CFO": (0.0, 1.0),
}


def embed(text: str) -> Sequence[float]:
    return SPACE[text]


class Tick:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class CountingBackend:
    """Stands in for the model. Counts calls, because the whole point of the
    ladder is that the number of calls goes down."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def __call__(self, question: str, context: str, tier: Tier) -> tuple[str, int, int]:
        self.calls.append((question, tier.name))
        return (f"answer to {question}", 1000, 200)


def ladder(
    semantic: bool = False, max_cost_usd: float | None = None
) -> tuple[Ladder, CountingBackend]:
    backend = CountingBackend()
    tick = Tick()
    return (
        Ladder(
            backend=backend,
            exact=ExactCache(clock=tick),
            semantic=SemanticCache(embed=embed, threshold=0.95, clock=tick) if semantic else None,
            max_cost_usd=max_cost_usd,
        ),
        backend,
    )


def test_the_first_request_reaches_the_model():
    lad, backend = ladder()
    served = lad.ask("what is the refund policy")
    assert served.source == "model"
    assert len(backend.calls) == 1


def test_a_repeat_request_never_reaches_the_model():
    lad, backend = ladder()
    lad.ask("what is the refund policy")
    served = lad.ask("what is the refund policy")
    assert served.source == "exact-cache"
    assert served.cost_usd == 0.0
    assert len(backend.calls) == 1  # still one


def test_a_changed_context_is_a_miss_because_the_answer_would_change():
    lad, backend = ladder()
    lad.ask("what is the refund policy", context="handbook v1")
    lad.ask("what is the refund policy", context="handbook v2")
    assert len(backend.calls) == 2


def test_a_paraphrase_is_a_miss_without_the_semantic_rung():
    lad, backend = ladder(semantic=False)
    lad.ask("what is the refund policy")
    lad.ask("how do refunds work")
    assert len(backend.calls) == 2


def test_the_semantic_rung_catches_the_paraphrase_the_exact_one_missed():
    lad, backend = ladder(semantic=True)
    lad.ask("what is the refund policy")
    served = lad.ask("how do refunds work")
    assert served.source == "semantic-cache"
    assert len(backend.calls) == 1


def test_a_cache_hit_never_consults_the_router():
    """Ordering, asserted. Deciding which model to pay for is pointless work when
    you already have the answer — and putting the router first is a real mistake
    people make, because it reads like the 'main' logic."""
    lad, backend = ladder()
    lad.ask("what is the refund policy")
    served = lad.ask("what is the refund policy")
    assert served.tier == "none"
    assert served.reason == "exact key hit"


def test_caching_reduces_cost_per_request_without_touching_the_answer():
    lad, _ = ladder()
    first = lad.ask("what is the refund policy")
    second = lad.ask("what is the refund policy")
    assert second.answer == first.answer  # rung 2 cannot change an answer
    rep = report(lad)
    assert rep.cache_hit_rate == 0.5
    assert rep.cost_per_request == pytest.approx(first.cost_usd / 2)


def test_the_report_separates_the_tail_from_the_mean():
    lad, _ = ladder()
    for question in ("what is the refund policy", "who is our CFO"):
        lad.ask(question)
    lad.ask("what is the refund policy")  # a fast cache hit
    rep = report(lad)
    assert rep.requests == 3
    assert rep.p99_ms >= rep.p50_ms
    assert rep.by_source == {"model": 2, "exact-cache": 1}


def test_a_downgrade_is_counted_in_the_report():
    lad, _ = ladder(max_cost_usd=0.0)
    lad.ask("why did the migration fail and how do we compare designs")
    assert report(lad).downgrades == 1


def test_percentile_is_nearest_rank_and_safe_on_empty():
    assert percentile([10, 20, 30, 40], 50) == 20
    assert percentile([], 99) == 0.0


def test_an_empty_run_reports_zeroes_rather_than_dividing_by_zero():
    lad, _ = ladder()
    rep = report(lad)
    assert (rep.requests, rep.cost_per_request) == (0, 0.0)
    assert (rep.p99_ms, rep.cache_hit_rate) == (0.0, 0.0)


def test_the_gate_fails_on_the_tail_even_when_the_bill_looks_great():
    """Free and slow is still a failure. This is why the gate takes three bars."""
    rep = Report(
        requests=100,
        total_cost_usd=0.0,
        p50_ms=120.0,
        p95_ms=400.0,
        p99_ms=9000.0,
        cache_hit_rate=0.9,
        downgrades=0,
        by_source={"exact-cache": 90, "model": 10},
    )
    gate = budget_gate(
        rep, quality=0.99, p99_budget_ms=2000.0, cost_budget_usd=1.0, min_quality=0.9
    )
    assert not gate.passed
    assert any("p99" in reason for reason in gate.reasons)


def test_the_gate_fails_when_a_saving_cost_quality():
    lad, _ = ladder()
    lad.ask("what is the refund policy")
    gate = budget_gate(
        report(lad),
        quality=0.81,  # the cheap tier answered, and scored worse
        p99_budget_ms=10_000.0,
        cost_budget_usd=1.0,
        min_quality=0.90,
    )
    assert not gate.passed
    assert any("quality" in reason for reason in gate.reasons)


def test_the_gate_fails_when_cost_per_request_is_over_budget():
    lad, _ = ladder()
    lad.ask("why did the migration fail")  # routed to the frontier tier, so it bills
    gate = budget_gate(
        report(lad),
        quality=0.99,
        p99_budget_ms=10_000.0,
        cost_budget_usd=0.0000001,
        min_quality=0.9,
    )
    assert not gate.passed
    assert any("request" in reason for reason in gate.reasons)


def test_the_gate_reports_every_reason_it_failed_not_just_the_first():
    lad, _ = ladder()
    lad.ask("why did the migration fail")
    gate = budget_gate(
        report(lad),
        quality=0.10,
        p99_budget_ms=1.0,
        cost_budget_usd=0.0,
        min_quality=0.9,
    )
    assert not gate.passed
    assert len(gate.reasons) == 3
