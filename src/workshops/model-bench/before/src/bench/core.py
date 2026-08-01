"""The bench itself: run one task across candidates and rank them honestly.

The data shapes are given. The five functions that turn them into a defensible
ranking are yours.

Two design decisions are already baked into the types, and it is worth seeing why
before you start filling in bodies:

1. `Runner` is injected. Nothing in this module imports a vendor SDK, which is
   what lets the whole bench run offline against a fake.
2. `Row.cost_per_success` exists, and `Row.cost_usd` is not enough on its own.
   Ranking on raw spend rewards a model that fails cheaply. Think about what the
   right value is when `ok == 0`.
"""
from __future__ import annotations

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
    """A vendor-agnostic view of what one call cost, in tokens."""

    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int = 0


@dataclass(frozen=True)
class Reply:
    """What a runner hands back. Text plus the billing truth."""

    text: str
    usage: Usage


class Runner(Protocol):
    """Sends one prompt to one candidate. Raises on any failure."""

    def __call__(self, candidate: Candidate, prompt: str) -> Reply: ...


Validator = Callable[[str], bool]
Clock = Callable[[], float]


def cost(candidate: Candidate, usage: Usage) -> float:
    """Dollars for one call, computed from `usage` — never from an estimate.

    TODO: price the fresh input tokens, the cached ones (a hit bills at ~10% of
    the input rate) and the output tokens. Prices are per *million* tokens.
    This is lesson 02's meter; if you wrote it there, bring it here.
    """
    raise NotImplementedError


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
    """Nearest-rank percentile — no interpolation, and 0.0 for an empty input.

    TODO: sort, pick the rank, clamp the index so p=0 and p=100 both land inside
    the list. Resist the urge to reach for `statistics.quantiles`: with four
    samples, interpolation invents latencies nobody measured.
    """
    raise NotImplementedError


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

        TODO: total spend divided by the answers you can actually use. Decide
        what zero successes means — and make sure `sorted()` agrees with you.
        """
        raise NotImplementedError


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
    """One call, timed and billed.

    TODO: this must never raise. A provider that times out is a row with
    `ok=False` and the exception in `error` — a bench that dies on the first bad
    vendor tells you nothing about the other three. Time the call with `clock`
    (injected so tests can script latency), and remember that a reply which
    arrives but violates the schema is *also* a failure that still cost money.
    """
    raise NotImplementedError


def run_bench(
    candidates: Iterable[Candidate],
    cases: Sequence[str],
    runner: Runner,
    validate: Validator,
    task: str = "task",
    clock: Clock = time.perf_counter,
) -> BenchRun:
    """Every candidate against every case, aggregated into one row each.

    TODO: run the cases, then fold the results into a `Row` — summed tokens and
    cost, counted successes, p50 and max latency, and the collected errors.
    """
    raise NotImplementedError


def rank(run: BenchRun) -> list[Row]:
    """Cheapest *working* answer first, ties broken by latency.

    TODO: sort on `cost_per_success`. Total failures must sink to the bottom.
    """
    raise NotImplementedError
