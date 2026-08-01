"""Rung 4: send easy work to a cheap model, keep the frontier one for hard work.

Routing is the biggest lever on a mixed workload, because most requests are not
hard. It is also the rung most likely to quietly cost you quality, so two rules are
baked into the types here:

- a route carries a **reason**, so a cheap answer can be explained after the fact;
- a downgrade forced by a cost ceiling is **recorded as a downgrade**, not silently
  passed off as a routing decision. Those are different events when you are
  debugging why last Tuesday's answers were worse.
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
        return (tokens_in * self.price_in + tokens_out * self.price_out) / 1_000_000


LOCAL = Tier("local", "qwen3.5:9b", 0.0, 0.0)
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
    """A deliberately boring classifier: length and a few keywords.

    Boring is a feature. An LLM call to decide which LLM to call adds latency and
    cost to *every* request, and a heuristic you can read is a heuristic you can
    debug. Replace it with a trained classifier only once you have the eval scores
    to prove the heuristic is what's holding you back.
    """
    text = question.strip().lower()
    hard_markers = ("compare", "why", "trade-off", "tradeoff", "design", "explain how")
    if any(marker in text for marker in hard_markers) or len(text) > 280:
        return "frontier"
    if len(text) < 60:
        return "local"
    return "cheap"


def route(
    question: str,
    est_tokens_in: int,
    est_tokens_out: int,
    max_cost_usd: float | None = None,
    classifier: Classifier = classify,
) -> Decision:
    """Pick a tier, then respect the ceiling by walking *down* the price order.

    Note what this does when nothing fits: it returns the cheapest tier with the
    reason recorded, rather than raising. Refusing to answer because the budget is
    tight is rarely the behaviour you want in production — but silently answering
    from a worse model without saying so is worse. Hence `downgraded_from`.
    """
    wanted = classifier(question)
    tier = TIERS[wanted]
    if max_cost_usd is None or tier.cost(est_tokens_in, est_tokens_out) <= max_cost_usd:
        return Decision(tier=tier, reason=f"classified {wanted}")

    # Step down one rung at a time and stop at the first tier that fits. Falling
    # straight to the free tier would be cheaper and needlessly worse.
    below = ORDER[: ORDER.index(wanted)]
    for name in reversed(below):
        candidate = TIERS[name]
        if candidate.cost(est_tokens_in, est_tokens_out) <= max_cost_usd:
            return Decision(
                tier=candidate,
                reason=f"{wanted} exceeded the ${max_cost_usd:.4f} ceiling",
                downgraded_from=wanted,
            )
    return Decision(
        tier=TIERS[ORDER[0]],
        reason=f"nothing fits ${max_cost_usd:.4f}; using the cheapest tier",
        downgraded_from=wanted,
    )
