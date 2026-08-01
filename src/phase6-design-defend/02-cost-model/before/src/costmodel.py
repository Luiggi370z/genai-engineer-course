"""TODO: build the $/query cost model. Lever order matters: cache -> route -> compress.

- per_call_cost(tier, w): dollars for one call from the PRICE table.
- daily_cost(w, cache_hit_rate, local_share): apply the cache first (hits ~free),
  then route the remaining misses (local_share to the free tier, rest to frontier).

Reference: ../after/src/costmodel.py.
"""
from __future__ import annotations

from dataclasses import dataclass

PRICE = {"local": (0.0, 0.0), "cheap": (1.0, 5.0), "frontier": (5.0, 25.0)}


@dataclass
class Workload:
    queries_per_day: int
    in_tokens: int
    out_tokens: int


def per_call_cost(tier: str, w: Workload) -> float:
    raise NotImplementedError  # TODO 1


def daily_cost(w: Workload, cache_hit_rate: float = 0.0, local_share: float = 0.0) -> float:
    raise NotImplementedError  # TODO 2
