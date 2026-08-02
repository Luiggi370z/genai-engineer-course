"""The decision matrix — six dimensions, filled from measurements.

A framework comparison written from prose concludes whatever its author already
believed. Everyone's table says LangGraph is "durable" and CrewAI is "fast to
prototype", because that is what the docs say, and nobody has ever been talked
out of a framework by a table they wrote themselves.

So this one takes numbers. You run the same agent three ways
(`frameworks.py`), record what each run actually did, and the verdict is
*derived*. The interesting output is not the winner — it is `undecided()`.

## Why `undecided` is the point

Three dimensions out of six will usually come back undecided on a task this
small, and that is the honest result: your measurement did not separate them.
The failure this prevents is the one everybody makes — filling all six rows,
finding a winner in each, and mistaking a table of ties for evidence. If the
measurements do not distinguish the frameworks on latency, the correct thing to
write in the latency row is "not distinguished by this test", and the correct
next step is to decide whether that dimension matters enough to build a test
that would.

## Why these six

They are the dimensions that change an architecture rather than a preference.
Durability and recovery decide whether you need a database. Complexity and
observability decide what the next engineer's week looks like. Latency and cost
decide whether it ships. "Nice API" is not on the list, because it is the one
everybody rates first and the only one that stops mattering after a month.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
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
#: other are a tie, not a winner — declaring a 4% difference a victory is how a
#: matrix launders noise into a decision.
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


#: How to read each dimension off a measurement, and which direction wins.
#: Keeping it as data means adding a dimension is one line, and — more usefully
#: — means every dimension is scored the same way, so nobody's favourite gets a
#: bespoke rule.
_READ: dict[str, tuple[Callable[[Measured], float], bool]] = {
    "durability": (lambda m: float(m.resumable), True),
    "recovery": (lambda m: float(m.recovered), True),
    "complexity": (lambda m: float(m.glue_lines), False),
    "observability": (lambda m: float(m.spans), True),
    "latency": (lambda m: m.p50_ms, False),
    "cost": (lambda m: float(m.tokens), False),
}

#: Rendered yes/no. The rest are counts, where 1 means one span and 0 means no
#: tokens — not "yes" and "no".
_BOOLEAN = frozenset({"durability", "recovery"})


def value(row: Measured, dimension: str) -> float:
    if dimension not in _READ:
        raise MatrixError(f"no such dimension: {dimension!r}")
    return _READ[dimension][0](row)


def winner(rows: Sequence[Measured], dimension: str) -> str:
    """The framework this measurement actually favours, or `UNDECIDED`.

    Two ways to be undecided, and both are common: a tie on the best value, or a
    spread inside the noise floor. Reporting either as a winner is the specific
    dishonesty this function exists to prevent — a matrix is persuasive, and a
    persuasive artifact built on a 4% difference will outlive everyone's memory
    of how it was measured.
    """
    if not rows:
        raise MatrixError("nothing measured")
    read, higher_is_better = _READ[dimension]
    scored = [(read(row), row.framework) for row in rows]
    best = max(scored)[0] if higher_is_better else min(scored)[0]
    leaders = [name for score, name in scored if score == best]
    if len(leaders) > 1:
        return UNDECIDED
    spread = max(s for s, _ in scored) - min(s for s, _ in scored)
    scale = max(abs(s) for s, _ in scored) or 1.0
    if spread / scale < NOISE_RATIO:
        return UNDECIDED
    return leaders[0]


def undecided(rows: Sequence[Measured]) -> list[str]:
    """The dimensions this experiment did not separate.

    Read this before the winners. A dimension here is not a failure of the
    frameworks — it is a statement about your test, and the honest options are to
    build a harder one or to admit the dimension does not decide this choice."""
    return [d for d in DIMENSIONS if winner(rows, d) == UNDECIDED]


def render(rows: Sequence[Measured]) -> str:
    """The matrix as markdown, measurements included.

    The numbers stay in the table next to the verdict on purpose. A verdict
    without its measurement is prose again, and six months later nobody can tell
    whether "durable" meant "we tested resume" or "the docs said so".
    """
    if not rows:
        raise MatrixError("nothing measured")
    names = [row.framework for row in rows]
    lines = [
        "| dimension | " + " | ".join(names) + " | verdict |",
        "|---" * (len(names) + 2) + "|",
    ]
    for dimension in DIMENSIONS:
        cells = [_format(value(row, dimension), dimension) for row in rows]
        lines.append(f"| {dimension} | " + " | ".join(cells) + f" | {winner(rows, dimension)} |")
    return "\n".join(lines)


def _format(number: float, dimension: str) -> str:
    if dimension in _BOOLEAN:
        return "yes" if number else "no"
    return f"{number:.0f}" if number.is_integer() else f"{number:.1f}"


if __name__ == "__main__":
    # Illustrative numbers, not measured ones — replace them with your own run's
    # output. A matrix you did not measure is a matrix you did not learn from.
    measurements = [
        Measured("langgraph", True, True, 24, 6, 41.0, 0),
        Measured("pydantic-ai", False, False, 9, 3, 12.0, 0),
        Measured("crewai", False, False, 18, 1, 2400.0, 1850),
    ]
    print(render(measurements))
    print("\nundecided:", undecided(measurements) or "none")
