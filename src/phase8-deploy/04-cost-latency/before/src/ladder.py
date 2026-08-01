"""TODO: wire the ladder in order — exact cache → semantic cache → route → call.

The order is the lesson, and it is sorted by risk rather than by size of saving:

  1. prompt caching   (Phase 1) — cannot change an answer
  2. exact cache                — cannot change an answer, given a correct key
  3. semantic cache             — CAN change an answer; threshold is a quality call
  4. routing                    — CAN change an answer; needs a per-tier eval score

Take the safe rungs first. You may not need the risky ones — and if you do reach for
them, you'll know which rung to blame when the eval score moves.

Reference: ../after/src/ladder.py.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from .cache import ExactCache, SemanticCache
from .router import Tier

# Answers a question on a given tier, returning (text, tokens_in, tokens_out).
Backend = Callable[[str, str, Tier], tuple[str, int, int]]


@dataclass(frozen=True)
class Served:
    """One request's receipt. Everything a later argument might need."""

    answer: str
    source: str  # "exact-cache" | "semantic-cache" | "model"
    tier: str
    cost_usd: float
    latency_ms: float
    reason: str = ""
    downgraded_from: str | None = None


@dataclass
class Ladder:
    """The request path with every rung attached, and a log of what each one did."""

    backend: Backend
    exact: ExactCache
    semantic: SemanticCache | None = None
    max_cost_usd: float | None = None
    cache_latency_ms: float = 3.0
    served: list[Served] = field(default_factory=list)

    def ask(self, question: str, context: str = "") -> Served:
        """TODO 1: the rungs, in order.

        - exact cache first (cost 0, tier "none", source "exact-cache")
        - then the semantic cache, and only if one was supplied
        - only *then* route, because deciding which model to pay for is pointless
          work when you already have the answer. Putting the router first is a real
          mistake people make, because it reads like the "main" logic.
        - on a model answer: bill it from the tier, write BOTH caches, and record
          the downgrade if the router made one.

        Append every `Served` to `self.served` — the log is what `report` reads.
        """
        raise NotImplementedError

    def _record(self, served: Served) -> Served:
        self.served.append(served)
        return served


def _estimate_tokens(text: str) -> int:
    """~4 characters per token. Fine for a routing estimate, useless for billing —
    the real cost comes off `usage` after the call (Phase 1, lesson 02)."""
    return max(1, len(text) // 4)


def _latency_of(tier: Tier) -> float:
    """A stand-in latency model so the fast tier is deterministic. In production
    this number comes off the span, never out of a table."""
    return {"local": 900.0, "cheap": 450.0, "frontier": 1400.0}.get(tier.name, 800.0)


# --- reporting -------------------------------------------------------------


def percentile(values: Sequence[float], p: float) -> float:
    """TODO 2: nearest-rank percentile, 0.0 on empty. No interpolation.
    The rank is ceil(p/100 * n) — not round(), which shifts ties to even."""
    raise NotImplementedError


@dataclass(frozen=True)
class Report:
    requests: int
    total_cost_usd: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    cache_hit_rate: float
    downgrades: int
    by_source: dict[str, int]

    @property
    def cost_per_request(self) -> float:
        return self.total_cost_usd / self.requests if self.requests else 0.0


def report(ladder: Ladder) -> Report:
    """TODO 3: fold the log into a Report. Zeroes on an empty run, not a crash."""
    raise NotImplementedError


@dataclass(frozen=True)
class Gate:
    """The pair, always. A cost saving reported without a quality score is a
    quality cut you have not measured yet."""

    passed: bool
    reasons: list[str]


def budget_gate(
    rep: Report,
    quality: float,
    p99_budget_ms: float,
    cost_budget_usd: float,
    min_quality: float,
) -> Gate:
    """TODO 4: fail on the tail, on the bill, or on the eval score.

    Collect **every** reason it failed, not just the first — a gate that reports one
    problem per run turns one fix into three round trips.

    `quality` comes from your Phase-3 suite, not from this module. Keep it that way:
    the thing measuring the saving must not be the thing certifying the quality.
    """
    raise NotImplementedError
