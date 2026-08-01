"""Caching, including the failure that makes semantic caching dangerous.

The embedder is scripted, so similarity is a number we chose. That is the only way
to write an honest test about a threshold: with a real embedder you would be
asserting facts about BGE rather than about your own cache.
"""
from __future__ import annotations

from collections.abc import Sequence

import pytest

from src.cache import ExactCache, SemanticCache, cache_key, cosine, sweep

# A three-axis toy space: axis 0 is "refunds", axis 1 "EU", axis 2 "US". The
# jurisdiction pair sits at ~0.94 — close enough to be reused by a loose threshold,
# which is exactly the situation that makes semantic caching risky in real life.
SPACE: dict[str, Sequence[float]] = {
    "what is the refund policy": (1.0, 0.0, 0.0),
    "how do refunds work": (0.99, 0.14, 0.0),  # a true paraphrase, ~0.99
    "what is the refund policy in the EU": (0.97, 0.245, 0.0),
    "what is the refund policy in the US": (0.97, 0.0, 0.245),  # ~0.94 against the EU one
    "who is our CFO": (0.0, 0.0, 1.0),
}


def embed(text: str) -> Sequence[float]:
    return SPACE[text]


class Tick:
    """A clock we advance by hand, so TTL tests don't sleep."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_the_key_covers_the_context_not_just_the_question():
    """The classic cache bug: re-index the document, keep serving the old answer."""
    a = cache_key("what is the policy", context="v1 of the handbook", model="gpt-5.2")
    b = cache_key("what is the policy", context="v2 of the handbook", model="gpt-5.2")
    assert a != b


def test_the_key_ignores_case_and_surrounding_whitespace():
    assert cache_key("  What Is The Policy ", "c", "m") == cache_key("what is the policy", "c", "m")


def test_the_key_covers_the_model_because_the_answer_depends_on_it():
    assert cache_key("q", "c", "gpt-5.2") != cache_key("q", "c", "qwen3.5:8b")


def test_an_exact_hit_returns_the_stored_answer():
    cache = ExactCache(clock=Tick())
    cache.put("k", "42")
    assert cache.get("k") == "42"
    assert cache.hit_rate == 1.0


def test_an_expired_entry_is_a_miss_and_is_dropped():
    tick = Tick()
    cache = ExactCache(ttl_s=300.0, clock=tick)
    cache.put("k", "42")
    tick.now = 301.0
    assert cache.get("k") is None
    assert "k" not in cache.entries  # dropped, not re-checked forever


def test_hit_rate_is_zero_before_any_traffic():
    assert ExactCache().hit_rate == 0.0


def test_cosine_is_one_for_identical_vectors_and_zero_for_orthogonal_ones():
    assert cosine((1.0, 0.0), (2.0, 0.0)) == pytest.approx(1.0)
    assert cosine((1.0, 0.0), (0.0, 1.0)) == pytest.approx(0.0)
    assert cosine((0.0, 0.0), (1.0, 1.0)) == 0.0  # no division by zero


def test_a_paraphrase_reuses_the_stored_answer():
    cache = SemanticCache(embed=embed, threshold=0.95, clock=Tick())
    cache.put("what is the refund policy", "30 days, unopened")
    assert cache.get("how do refunds work") == "30 days, unopened"


def test_an_unrelated_question_does_not_reuse_it():
    cache = SemanticCache(embed=embed, threshold=0.95, clock=Tick())
    cache.put("what is the refund policy", "30 days, unopened")
    assert cache.get("who is our CFO") is None


def test_a_loose_threshold_answers_the_wrong_question():
    """The whole risk of rung 3, in one test.

    'refund policy in the EU' and 'in the US' are close in embedding space and have
    different answers. At 0.95 the cache stays quiet; drop to 0.85 and it
    confidently serves EU law to a US customer. Nothing crashes. Nobody is paged.
    """
    strict = SemanticCache(embed=embed, threshold=0.95, clock=Tick())
    strict.put("what is the refund policy in the EU", "14-day statutory right")
    assert strict.get("what is the refund policy in the US") is None

    loose = SemanticCache(embed=embed, threshold=0.85, clock=Tick())
    loose.put("what is the refund policy in the EU", "14-day statutory right")
    assert loose.get("what is the refund policy in the US") == "14-day statutory right"


def test_semantic_entries_also_expire():
    tick = Tick()
    cache = SemanticCache(embed=embed, threshold=0.9, ttl_s=60.0, clock=tick)
    cache.put("what is the refund policy", "30 days")
    tick.now = 61.0
    assert cache.get("how do refunds work") is None
    assert cache.entries == []


def test_nearest_reports_the_score_regardless_of_the_threshold():
    cache = SemanticCache(embed=embed, threshold=0.99, clock=Tick())
    cache.put("what is the refund policy", "30 days")
    best = cache.nearest("how do refunds work")
    assert best is not None
    assert 0.95 < best[1] < 1.0  # would have been reused at a looser threshold


def test_sweeping_the_threshold_shows_where_precision_breaks():
    """Pick the threshold with evidence, the way Phase 3 picks a judge threshold."""
    rows = sweep(
        embed=embed,
        stored=[("what is the refund policy in the EU", "14-day statutory right")],
        probes=[
            ("what is the refund policy in the EU", True),
            ("what is the refund policy in the US", False),  # reusing this is WRONG
            ("who is our CFO", False),
        ],
        thresholds=[0.99, 0.90, 0.80],
    )
    by_threshold = {row.threshold: row for row in rows}
    assert by_threshold[0.99].reuses == 1  # only the identical question
    assert by_threshold[0.99].wrong_reuses == 0
    assert by_threshold[0.80].wrong_reuses == 1  # bought hit rate with a wrong answer
    assert by_threshold[0.99].precision == 1.0
    assert by_threshold[0.80].precision < 1.0
