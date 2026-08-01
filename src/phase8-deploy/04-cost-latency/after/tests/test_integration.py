"""The opt-in tier: the semantic cache against a real embedding model.

    make test-integration     # downloads a small ONNX model on first run

The fast tier scripts similarity, which is right for testing the cache's *logic*.
It cannot tell you whether 0.95 is a sensible threshold for real English — only a
real embedder can, and the answer depends on your corpus. That is the honest reason
this tier exists: the threshold you ship has to be measured, not inherited.
"""
from __future__ import annotations

from collections.abc import Sequence

import pytest

from src.cache import SemanticCache, sweep

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def embed():
    from fastembed import TextEmbedding

    model = TextEmbedding("BAAI/bge-small-en-v1.5")

    def embed_one(text: str) -> Sequence[float]:
        return list(next(iter(model.embed([text]))))

    return embed_one


def test_a_real_paraphrase_is_reused(embed):
    cache = SemanticCache(embed=embed, threshold=0.90, ttl_s=float("inf"))
    cache.put("What is the refund policy?", "30 days, unopened.")
    assert cache.get("How do refunds work?") == "30 days, unopened."


def test_an_unrelated_question_is_not_reused(embed):
    cache = SemanticCache(embed=embed, threshold=0.90, ttl_s=float("inf"))
    cache.put("What is the refund policy?", "30 days, unopened.")
    assert cache.get("Who is our chief financial officer?") is None


def test_the_jurisdiction_pair_is_uncomfortably_close_in_real_embedding_space(embed):
    """The number that should make you cautious about semantic caching.

    Two questions with genuinely different answers — EU versus US refund law —
    score high, because embeddings capture topic far better than they capture the
    one word that changes the answer. Print it and look at it.
    """
    cache = SemanticCache(embed=embed, threshold=0.99, ttl_s=float("inf"))
    cache.put("What is the refund policy in the EU?", "14-day statutory right.")
    best = cache.nearest("What is the refund policy in the US?")
    assert best is not None
    print(f"\nEU vs US similarity: {best[1]:.3f}")
    assert best[1] > 0.85, "if this is low, re-check the embedder — it should be high"


def test_sweeping_on_real_vectors_produces_a_threshold_you_can_defend(embed):
    rows = sweep(
        embed=embed,
        stored=[("What is the refund policy in the EU?", "14-day statutory right.")],
        probes=[
            ("What is the refund policy in the EU?", True),
            ("How do EU refunds work?", True),
            ("What is the refund policy in the US?", False),
            ("Who is our chief financial officer?", False),
        ],
        thresholds=[0.99, 0.95, 0.90, 0.85, 0.80],
    )
    for row in rows:
        print(f"{row.threshold:.2f}  reuses={row.reuses}  wrong={row.wrong_reuses}")
    # Loosening the threshold can only ever reuse more, never less.
    assert [r.reuses for r in rows] == sorted(r.reuses for r in rows)
    assert rows[0].wrong_reuses <= rows[-1].wrong_reuses
