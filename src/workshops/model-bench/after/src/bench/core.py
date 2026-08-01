"""The bench itself: run one task across candidates and rank them honestly.

Two decisions carry this module.

First, a candidate is *data*, not a code path. `Runner` is the only thing that
knows how to talk to a vendor, and it is injected — which is why the whole bench
is testable offline against a fake, and why adding a provider is a dict entry.

Second, the ranking metric is **cost per successful parse**, not price per token.
A model at a tenth of the price that fails a third of the time is not cheap; it
is a retry loop wearing a discount. Ranking on raw price is the single most
common way a bench lies to you.
"""
from __future__ import annotations

import math
import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class Candidate:
    """One thing under test: a model, where it lives, and what it charges."""

    name: str  # the config key you type on the CLI: "local", "gpt", "claude"
    model: str
    price_in: float  # $ per million input tokens ($0 for local)
    price_out: float  # $ per million output tokens


@dataclass(frozen=True)
class Usage:
    """A vendor-agnostic view of what one call cost, in tokens.

    Same shape as `phase1-foundations/02-token-cost-meter` on purpose: the meter
    you wrote in lesson 02 is the meter the bench bills with.
    """

    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int = 0


@dataclass(frozen=True)
class Reply:
    """What a runner hands back. Text plus the billing truth."""

    text: str
    usage: Usage


class Runner(Protocol):
    """Sends one prompt to one candidate. Raises on any failure.

    Raising rather than returning an error is deliberate: a runner's job is to
    talk to a vendor, and deciding what a timeout *means* for the report is the
    bench's job, not the transport's.
    """

    def __call__(self, candidate: Candidate, prompt: str) -> Reply: ...


Validator = Callable[[str], bool]
Clock = Callable[[], float]


def cost(candidate: Candidate, usage: Usage) -> float:
    """Dollars for one call, computed from `usage` — never from an estimate."""
    cached = usage.cache_read_input_tokens
    fresh = usage.input_tokens - cached
    return (
        fresh * candidate.price_in
        + cached * candidate.price_in * 0.1  # a cache hit bills at ~10% of input
        + usage.output_tokens * candidate.price_out
    ) / 1_000_000


@dataclass(frozen=True)
class Result:
    """One candidate, one case."""

    candidate: str
    ok: bool  # the reply arrived AND satisfied the validator
    latency_ms: float
    cost_usd: float
    tokens_in: int = 0
    tokens_out: int = 0
    error: str | None = None


def percentile(values: Sequence[float], p: float) -> float:
    """Nearest-rank percentile. Small-n honest: no interpolation, no pretending.

    Rank is ceil(p/100 * n), the textbook rule. `round()` looks equivalent but
    Python rounds ties to even, which mis-picks the index on exact ranks —
    P50 of two samples would report the max."""
    if not values:
        return 0.0
    ordered = sorted(values)
    k = max(0, min(len(ordered) - 1, math.ceil(p / 100 * len(ordered)) - 1))
    return ordered[k]


@dataclass
class Row:
    """One candidate's aggregate across every case."""

    candidate: str
    model: str
    cases: int
    ok: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    p50_ms: float
    max_ms: float
    errors: list[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        return self.ok / self.cases if self.cases else 0.0

    @property
    def cost_per_success(self) -> float:
        """The number that decides the ranking.

        Zero successes is `inf`, not zero — a model that never works is
        infinitely expensive per working answer, and sorting must agree.
        """
        return self.cost_usd / self.ok if self.ok else float("inf")


@dataclass
class BenchRun:
    task: str
    rows: list[Row]

    @property
    def total_cost(self) -> float:
        return sum(r.cost_usd for r in self.rows)


def run_case(
    candidate: Candidate,
    prompt: str,
    runner: Runner,
    validate: Validator,
    clock: Clock = time.perf_counter,
) -> Result:
    """One call, timed and billed. Never raises — a dead provider is a data point."""
    started = clock()
    try:
        reply = runner(candidate, prompt)
    except Exception as exc:  # noqa: BLE001 - a vendor failure is a row, not a crash
        return Result(
            candidate=candidate.name,
            ok=False,
            latency_ms=(clock() - started) * 1000,
            cost_usd=0.0,  # a failed call may still bill, but we cannot know from here
            error=f"{type(exc).__name__}: {exc}",
        )
    elapsed_ms = (clock() - started) * 1000
    ok = validate(reply.text)
    return Result(
        candidate=candidate.name,
        ok=ok,
        latency_ms=elapsed_ms,
        cost_usd=cost(candidate, reply.usage),
        tokens_in=reply.usage.input_tokens,
        tokens_out=reply.usage.output_tokens,
        error=None if ok else "schema violation",
    )


def run_bench(
    candidates: Iterable[Candidate],
    cases: Sequence[str],
    runner: Runner,
    validate: Validator,
    task: str = "task",
    clock: Clock = time.perf_counter,
) -> BenchRun:
    """Every candidate against every case. One row per candidate."""
    rows: list[Row] = []
    for candidate in candidates:
        results = [run_case(candidate, case, runner, validate, clock) for case in cases]
        latencies = [r.latency_ms for r in results]
        rows.append(
            Row(
                candidate=candidate.name,
                model=candidate.model,
                cases=len(results),
                ok=sum(1 for r in results if r.ok),
                tokens_in=sum(r.tokens_in for r in results),
                tokens_out=sum(r.tokens_out for r in results),
                cost_usd=sum(r.cost_usd for r in results),
                p50_ms=percentile(latencies, 50),
                max_ms=max(latencies) if latencies else 0.0,
                errors=[r.error for r in results if r.error],
            )
        )
    return BenchRun(task=task, rows=rows)


def rank(run: BenchRun) -> list[Row]:
    """Cheapest *working* answer first. Total failures sink to the bottom."""
    return sorted(run.rows, key=lambda r: (r.cost_per_success, r.p50_ms))
