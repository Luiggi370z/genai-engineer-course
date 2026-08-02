"""TODO: what a request consumed, and what that costs.

One meter, used twice: `core.py` puts these numbers on the compose span, and
`report.py` totals them for the CI cost gate. Two meters would be two answers to
"what did last week cost", and the interesting week is always the one where they
disagree.

The price table is `crew.PRICE` — the same tiers the Phase-5 crew routes across —
rather than a second copy here. `local` is (0.0, 0.0) and that is the honest
number for a self-hosted model: no per-token invoice exists. It is not a licence
to stop counting. Count tokens regardless, so pointing the composer at a paid API
and setting `ASSISTANT_PRICE_TIER` turns the same measurement into a bill the
merge gate can block on, with no new instrumentation.

Reference: ../../after/src/assistant/usage.py.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Usage:
    tokens_in: int
    tokens_out: int

    @property
    def total(self) -> int:
        return self.tokens_in + self.tokens_out

    def cost(self, tier: str) -> float:
        """TODO 1: USD for this exchange at that tier's prices.

        `PRICE` is per million tokens, as `(price_in, price_out)`. An unknown
        tier costs nothing, which is the safe direction for a REPORT — a made-up
        price is worse than a missing one — and the reason `settings.price_tier`
        is documented next to the tiers that exist. Round to six places.
        """
        raise NotImplementedError


def measure(prompt: str, completion: str) -> Usage:
    """TODO 2: tokens in and out for one model exchange.

    Use `count_tokens`, the same approximation the context budget uses
    (memory.py). Sharing it means the budget and the bill are denominated in the
    same unit; a real tokenizer swaps in there and both follow.
    """
    raise NotImplementedError
