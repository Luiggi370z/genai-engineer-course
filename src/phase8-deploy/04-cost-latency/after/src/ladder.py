"""The ladder, wired in order: exact cache → semantic cache → route → call.

The order is the lesson. It is sorted by risk, not by size of saving:

  1. prompt caching   (Phase 1) — cannot change an answer
  2. exact cache                — cannot change an answer, given a correct key
  3. semantic cache             — CAN change an answer; threshold is a quality call
  4. routing                    — CAN change an answer; needs a per-tier eval score

Take the safe rungs first. You may not need the risky ones, and if you do reach for
them, you now know which rung to blame when the eval score moves.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from .cache import ExactCache, SemanticCache, cache_key
from .router import Decision, Tier, route

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
        # Rung 2. Cheapest possible outcome: no model call at all.
        key = cache_key(question, context, "any")
        hit = self.exact.get(key)
        if hit is not None:
            return self._record(
                Served(hit, "exact-cache", "none", 0.0, self.cache_latency_ms, "exact key hit")
            )

        # Rung 3. Only reached on an exact miss, and only if you opted in.
        if self.semantic is not None:
            near = self.semantic.get(question)
            if near is not None:
                return self._record(
                    Served(
                        near,
                        "semantic-cache",
                        "none",
                        0.0,
                        self.cache_latency_ms,
                        f"similar question above {self.semantic.threshold}",
                    )
                )

        # Rung 4. Now, and only now, do we decide which model to pay for.
        decision: Decision = route(
            question,
            est_tokens_in=_estimate_tokens(question + context),
            est_tokens_out=200,
            max_cost_usd=self.max_cost_usd,
        )
        answer, tokens_in, tokens_out = self.backend(question, context, decision.tier)
        cost = decision.tier.cost(tokens_in, tokens_out)

        self.exact.put(key, answer)
        if self.semantic is not None:
            self.semantic.put(question, answer)

        return self._record(
            Served(
                answer=answer,
                source="model",
                tier=decision.tier.name,
                cost_usd=cost,
                latency_ms=_latency_of(decision.tier),
                reason=decision.reason,
                downgraded_from=decision.downgraded_from,
            )
        )

    def _record(self, served: Served) -> Served:
        self.served.append(served)
        return served


def _estimate_tokens(text: str) -> int:
    """~4 characters per token. Fine for a routing estimate, useless for billing —
    the actual cost comes off `usage` after the call (Phase 1, lesson 02)."""
    return max(1, len(text) // 4)


def _latency_of(tier: Tier) -> float:
    """A stand-in latency model so the fast tier is deterministic. In production
    this number comes off the span, never out of a table."""
    return {"local": 900.0, "cheap": 450.0, "frontier": 1400.0}.get(tier.name, 800.0)


# --- reporting -------------------------------------------------------------


def percentile(values: Sequence[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, round(p / 100 * len(ordered) + 0.5) - 1))
    return ordered[idx]


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
    served = ladder.served
    latencies = [s.latency_ms for s in served]
    by_source: dict[str, int] = {}
    for s in served:
        by_source[s.source] = by_source.get(s.source, 0) + 1
    cached = sum(count for source, count in by_source.items() if source.endswith("cache"))
    return Report(
        requests=len(served),
        total_cost_usd=sum(s.cost_usd for s in served),
        p50_ms=percentile(latencies, 50),
        p95_ms=percentile(latencies, 95),
        p99_ms=percentile(latencies, 99),
        cache_hit_rate=cached / len(served) if served else 0.0,
        downgrades=sum(1 for s in served if s.downgraded_from),
        by_source=by_source,
    )


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
    """Fail loudly on the tail, on the bill, or on the eval score.

    `quality` comes from your Phase-3 suite, not from this module. That separation
    is deliberate: the thing measuring the saving must not be the thing certifying
    the quality.
    """
    reasons: list[str] = []
    if rep.p99_ms > p99_budget_ms:
        reasons.append(f"p99 {rep.p99_ms:.0f}ms over the {p99_budget_ms:.0f}ms budget")
    if rep.cost_per_request > cost_budget_usd:
        reasons.append(
            f"${rep.cost_per_request:.5f}/request over the ${cost_budget_usd:.5f} budget"
        )
    if quality < min_quality:
        reasons.append(f"quality {quality:.3f} below the {min_quality:.3f} bar")
    return Gate(passed=not reasons, reasons=reasons)
