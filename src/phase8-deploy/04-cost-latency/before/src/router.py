"""TODO: rung 4 — send easy work to a cheap model, keep the frontier one for hard work.

Routing is the biggest lever on a mixed workload, because most requests are not
hard. It is also the rung most likely to quietly cost you quality, so two rules are
already baked into the types:

- a route carries a **reason**, so a cheap answer can be explained after the fact;
- a downgrade forced by a cost ceiling is recorded **as a downgrade**, not passed
  off as a routing decision. Those are different events when you are debugging why
  last Tuesday's answers were worse.

Reference: ../after/src/router.py.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class Tier:
    name: str
    model: str
    price_in: float  # $/MTok
    price_out: float

    def cost(self, tokens_in: int, tokens_out: int) -> float:
        """TODO 1: dollars for this tier. Prices are per million tokens."""
        raise NotImplementedError


LOCAL = Tier("local", "qwen3.5:8b", 0.0, 0.0)
CHEAP = Tier("cheap", "gpt-5.4-mini", 0.25, 2.00)
FRONTIER = Tier("frontier", "gpt-5.2", 1.75, 14.00)

TIERS: dict[str, Tier] = {t.name: t for t in (LOCAL, CHEAP, FRONTIER)}
ORDER = ("local", "cheap", "frontier")  # cheapest first


@dataclass(frozen=True)
class Decision:
    tier: Tier
    reason: str
    downgraded_from: str | None = None


Classifier = Callable[[str], str]


def classify(question: str) -> str:
    """TODO 2: return a tier name from "local" | "cheap" | "frontier".

    Keep it boring — length plus a few keywords ("compare", "why", "trade-off",
    "design", "explain how"). Boring is a feature: an LLM call to decide which LLM
    to call adds cost and latency to *every* request, and a heuristic you can read
    is one you can debug. Reach for a trained classifier only once you have eval
    scores proving the heuristic is what's holding you back.
    """
    raise NotImplementedError


def route(
    question: str,
    est_tokens_in: int,
    est_tokens_out: int,
    max_cost_usd: float | None = None,
    classifier: Classifier = classify,
) -> Decision:
    """TODO 3: classify, then respect the ceiling by stepping DOWN one rung at a time.

    Two judgement calls to get right:

    - Step down to the first tier that fits, not straight to the free one. Falling
      to `local` when `cheap` would have fit is needlessly worse.
    - When nothing fits, return the cheapest tier rather than raising. Refusing to
      answer because the budget is tight is rarely what you want — but silently
      answering from a worse model is worse still. That's what `downgraded_from`
      is for: record it.
    """
    raise NotImplementedError
