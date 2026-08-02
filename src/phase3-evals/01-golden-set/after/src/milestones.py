"""Fifty rows, in three sittings — and what each sitting is allowed to tell you.

"Write fifty golden rows" is the instruction most people abandon. Not because it
is hard, but because it is shapeless: there is no feedback until the end, and a
task with no feedback for four hours is a task you do once and never again.

So it comes in three: **10, 25, 50**. Each is a real stopping point, each gets
scored, and each comes with the honest statement of what a score at that `n` can
support. That last part is the actual lesson. The milestones are motivation; the
interval is the content.

## Why an interval and not a number

A score is a proportion measured on a sample, so it carries a sampling error, and
at these sample sizes the error is enormous. 8 of 10 is not "0.80". It is 0.80
with a 95% interval of roughly 0.49–0.94 — a system that is genuinely mediocre
and one that is genuinely good both produce 8/10 often enough that you cannot
tell them apart. Quote 0.80 from ten rows and you have said something false in a
way that sounds rigorous.

This is not an argument against small sets. Ten rows is enormously better than
zero, and it will find your obvious bugs on the first afternoon. It is an
argument against *quoting* a small set as though it were a measurement, and
against the specific failure that follows: watching a number move from 0.80 to
0.85 between runs and shipping a change because of it, when the interval says
those are the same result.

The Wilson interval is used rather than the textbook normal approximation, which
is genuinely broken at small `n` — at 10/10 it gives ±0.00, confidently reporting
perfection from ten questions, and it can produce bounds below 0 or above 1.
Wilson stays inside [0, 1] and never claims certainty it has not earned.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

#: The three sittings. Ten is one sitting and finds the obvious bugs; twenty-five
#: is where slice-level shape appears; fifty is the smallest set worth gating on.
MILESTONES = (10, 25, 50)

#: 95%. Kept as a constant because the interval is meaningless without saying so.
Z = 1.959963984540054


class MilestoneError(Exception):
    """A refusal to score. Raised where a number would be worse than nothing."""


@dataclass(frozen=True)
class Interval:
    """A measured proportion, with the range the sample actually supports."""

    passed: int
    n: int

    @property
    def score(self) -> float:
        return self.passed / self.n

    @property
    def bounds(self) -> tuple[float, float]:
        return wilson(self.passed, self.n)

    @property
    def width(self) -> float:
        low, high = self.bounds
        return high - low

    def indistinguishable_from(self, other: Interval) -> bool:
        """Do these two overlap? Then you cannot tell them apart, whatever the
        point estimates say — which is the check that stops a 0.80-to-0.85 move
        from being read as an improvement."""
        low, high = self.bounds
        other_low, other_high = other.bounds
        return low <= other_high and other_low <= high


def wilson(passed: int, n: int, z: float = Z) -> tuple[float, float]:
    """The Wilson score interval, clamped to [0, 1] by construction.

    Preferred over `p ± z·sqrt(p(1-p)/n)` for the reason that matters at n=10:
    the normal approximation returns a zero-width interval when every row passes,
    reporting certainty from ten questions. Wilson pulls the estimate toward 0.5
    in proportion to how little data there is, which is exactly the behaviour you
    want from something whose job is to stop you overclaiming.
    """
    if n <= 0:
        raise MilestoneError("no rows scored — there is nothing to put an interval on")
    if not 0 <= passed <= n:
        raise MilestoneError(f"{passed} passed out of {n} is not a proportion")
    p = passed / n
    denominator = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denominator
    spread = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denominator
    return (max(0.0, centre - spread), min(1.0, centre + spread))


def verdict(n: int) -> str:
    """What a score at this sample size is allowed to be used for.

    Deliberately about `n` alone, not the score. The temptation at every milestone
    is to let a good number buy conclusions the sample size does not support, and
    a rule that reads the score would be exactly the loophole.
    """
    if n < MILESTONES[0]:
        return "not yet a measurement — finish the first ten"
    if n < MILESTONES[1]:
        return (
            "smoke test. Enough to find obvious breakage and to prove the harness "
            "runs end to end. Not enough to compare two systems, and not enough to "
            "quote"
        )
    if n < MILESTONES[2]:
        return (
            "shape. Per-slice differences start to mean something, so this is where "
            "you learn which slice is dragging the average. Still too noisy to gate a "
            "merge on"
        )
    return (
        "gateable. Wide enough to hold a per-slice signal and narrow enough that a "
        "real regression clears the interval. This is the floor, not the target"
    )


def reached(n: int) -> int | None:
    """The highest milestone this row count has passed, or `None`."""
    hit = [m for m in MILESTONES if n >= m]
    return hit[-1] if hit else None


def progress(rows: int) -> str:
    """One line for the top of the report: where you are and what is next."""
    done = reached(rows)
    if done is None:
        return f"{rows}/{MILESTONES[0]} rows — {MILESTONES[0] - rows} to the first milestone"
    if done == MILESTONES[-1]:
        return f"{rows} rows — all milestones reached"
    nxt = next(m for m in MILESTONES if m > rows)
    return f"{rows} rows — milestone {done} reached, {nxt - rows} to {nxt}"


def render(interval: Interval, label: str = "overall") -> str:
    """The scoreline, with its interval and its licence, on one line.

    The three parts are inseparable on purpose. A score without an interval
    invites overclaiming and an interval without a verdict leaves the reader to
    guess what it licenses — and readers guess generously about their own work.
    """
    low, high = interval.bounds
    return (
        f"{label}: {interval.score:.2f} "
        f"(95% CI {low:.2f}–{high:.2f}, n={interval.n}) — {verdict(interval.n)}"
    )
