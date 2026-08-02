"""TODO: score the three frameworks on six dimensions, from measurements.

A framework comparison written from prose concludes whatever its author already
believed. Everyone's table says LangGraph is "durable" and CrewAI is "fast to
prototype", because that is what the docs say, and nobody has ever been talked
out of a framework by a table they wrote themselves.

So this one takes numbers. You run the same agent three ways (`frameworks.py`),
record what each run actually did, and the verdict is *derived*. The interesting
output is not the winner — it is `undecided()`.

## Why `undecided` is the point

Three dimensions out of six will usually come back undecided on a task this
small, and that is the honest result: your measurement did not separate them.
The failure this prevents is the one everybody makes — filling all six rows,
finding a winner in each, and mistaking a table of ties for evidence.

## The TODOs

1. `value` — read one dimension off a measurement (and reject unknown ones).
2. `winner` — the framework the measurement favours, or `UNDECIDED`. TWO ways to
   be undecided: a tie on the best value, and a spread inside `NOISE_RATIO`.
   Both are common; reporting either as a win is the dishonesty to avoid.
3. `undecided` — every dimension this experiment did not separate.
4. `render` — markdown, with the measurement kept beside the verdict.

The tests in tests/test_matrix.py are the spec, and they run offline — you can
finish this file before installing a single framework.

Reference: ../after/src/matrix.py.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

#: Ordered, because the order is an argument: the two that decide whether you
#: need a database, then the two that decide what maintenance costs, then the
#: two that decide whether it ships.
DIMENSIONS = (
    "durability",
    "recovery",
    "complexity",
    "observability",
    "latency",
    "cost",
)

UNDECIDED = "not distinguished by this test"

#: Latency and cost measurements are noisy. Two runs within this ratio of each
#: other are a tie, not a winner.
NOISE_RATIO = 0.15


class MatrixError(Exception):
    """A refusal to score. Raised where a scored-but-wrong table would be worse
    than no table."""


@dataclass(frozen=True)
class Measured:
    """One framework's run, as numbers rather than adjectives.

    Every field is something you observed. `resumable` and `recovered` come back
    from `frameworks.Run` and from killing a run mid-flight; `glue_lines` is
    counted, not estimated; `spans` is how many the run emitted into your
    tracer; `p50_ms` and `tokens` are measured over repeats.
    """

    framework: str
    resumable: bool
    recovered: bool
    glue_lines: int
    spans: int
    p50_ms: float
    tokens: int


def value(row: Measured, dimension: str) -> float:
    raise NotImplementedError  # TODO 1


def winner(rows: Sequence[Measured], dimension: str) -> str:
    raise NotImplementedError  # TODO 2


def undecided(rows: Sequence[Measured]) -> list[str]:
    raise NotImplementedError  # TODO 3


def render(rows: Sequence[Measured]) -> str:
    raise NotImplementedError  # TODO 4
