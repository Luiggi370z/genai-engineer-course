"""$/query cost model with the levers in the right order: cache -> route -> compress.

Deterministic and offline. Shows how a cache hit rate and a local routing tier
change the bill for 100K queries/day.
"""
from __future__ import annotations

from dataclasses import dataclass

PRICE = {"local": (0.0, 0.0), "cheap": (1.0, 5.0), "frontier": (5.0, 25.0)}


@dataclass
class Workload:
    queries_per_day: int
    in_tokens: int          # avg input tokens per query
    out_tokens: int         # avg output tokens per query


def per_call_cost(tier: str, w: Workload) -> float:
    pin, pout = PRICE[tier]
    return (w.in_tokens * pin + w.out_tokens * pout) / 1_000_000


def daily_cost(
    w: Workload,
    cache_hit_rate: float = 0.0,
    local_share: float = 0.0,
    frontier_tier: str = "frontier",
) -> float:
    """Lever order: apply cache first (served free), then route the rest."""
    served = w.queries_per_day
    # 1. CACHE: hits cost ~nothing
    misses = served * (1 - cache_hit_rate)
    # 2. ROUTE: a share of misses go to the free local tier, rest to frontier
    local_calls = misses * local_share
    frontier_calls = misses * (1 - local_share)
    return (
        local_calls * per_call_cost("local", w)
        + frontier_calls * per_call_cost(frontier_tier, w)
    )


if __name__ == "__main__":
    w = Workload(queries_per_day=100_000, in_tokens=1500, out_tokens=500)
    base = daily_cost(w)
    tuned = daily_cost(w, cache_hit_rate=0.4, local_share=0.5)
    print(f"baseline/day: ${base:,.2f}")
    print(f"cache+route:  ${tuned:,.2f}  ({(1 - tuned / base) * 100:.0f}% cheaper)")
