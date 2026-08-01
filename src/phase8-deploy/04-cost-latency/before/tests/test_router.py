"""Routing, and the thing routing must never do quietly: downgrade in silence."""
from __future__ import annotations

import pytest

from src.router import CHEAP, FRONTIER, LOCAL, TIERS, classify, route


def test_a_short_lookup_goes_local():
    assert classify("what is the refund window?") == "local"


def test_a_reasoning_question_goes_frontier():
    assert classify("compare our refund policy with the EU statutory minimum") == "frontier"
    assert classify("why did the migration fail") == "frontier"


def test_a_long_question_goes_frontier_even_without_a_keyword():
    assert classify("summarise this " + "x" * 300) == "frontier"


def test_the_middle_ground_goes_to_the_cheap_hosted_tier():
    assert classify("summarise the attached handbook section on returns and exchanges") == "cheap"


def test_local_tokens_are_free_and_the_pricing_is_per_million():
    assert LOCAL.cost(1_000_000, 1_000_000) == 0.0
    assert CHEAP.cost(1_000_000, 0) == pytest.approx(0.25)
    assert FRONTIER.cost(0, 1_000_000) == pytest.approx(14.00)


def test_without_a_ceiling_the_classification_stands():
    decision = route("why did the migration fail", 1000, 200)
    assert decision.tier is FRONTIER
    assert decision.downgraded_from is None


def test_a_ceiling_steps_down_one_rung_not_all_the_way_to_free():
    """Cheaper is fine. Cheaper-and-not-mentioned is how a quality drop hides.

    A million tokens each way costs $15.75 on the frontier tier and $2.25 on the
    cheap one, so a $3 ceiling should land on `cheap` — dropping straight to the
    free local model would be needlessly worse.
    """
    decision = route("why did the migration fail", 1_000_000, 1_000_000, max_cost_usd=3.00)
    assert decision.tier is CHEAP
    assert decision.downgraded_from == "frontier"
    assert "ceiling" in decision.reason


def test_a_ceiling_nothing_paid_can_meet_falls_back_to_the_free_tier():
    decision = route("why did the migration fail", 1_000_000, 1_000_000, max_cost_usd=0.0)
    assert decision.tier is TIERS["local"]  # free, and still records the downgrade
    assert decision.downgraded_from == "frontier"


def test_a_generous_ceiling_is_not_a_downgrade():
    decision = route("why did the migration fail", 100, 20, max_cost_usd=10.0)
    assert decision.downgraded_from is None


def test_an_injected_classifier_replaces_the_heuristic_without_touching_route():
    decision = route("anything at all", 100, 20, classifier=lambda _: "cheap")
    assert decision.tier is CHEAP
