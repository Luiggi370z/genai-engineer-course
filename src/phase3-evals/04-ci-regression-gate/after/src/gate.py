"""The merge gate: the boring mechanical part that makes evals real.

An eval you run by hand when you remember to is a vibe with extra steps. This module
is what turns a results file into an exit code, and it checks four different things
because they catch four different bugs:

  1. **Absolute bars.** "Faithfulness must be >= 0.85." Catches a system that is
     simply not good enough, including on day one.
  2. **Regression against a committed baseline.** Catches slow rot — a bar alone
     lets you slide from 0.94 to 0.86 with every single PR passing.
  3. **Per-slice regression.** Catches the failure an average hides: overall 0.86
     while the unanswerable slice collapses from 1.00 to 0.40.
  4. **Instrument drift.** If the judge model, its temperature or the RAGAS version
     changed, the new number is not comparable to the baseline. That is not a
     regression, it is a re-baseline — and it should be a deliberate, reviewed commit.

`TOLERANCE` comes from lesson 3.3: the judge's disagreement rate with your own
labels, averaged over the suite. Gating tighter than your noise floor teaches people
to ignore the gate.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

BARS = {"faithfulness": 0.85, "context_recall": 0.80}

# From the calibration report in lesson 3.3 (kappa 0.65 at threshold 0.65 over 40
# hand-labeled rows). Recompute it when you re-calibrate; do not guess it.
TOLERANCE = 0.03

# A slice at zero is never noise, whatever the tolerance says.
COLLAPSE_FLOOR = 0.5


@dataclass(frozen=True)
class Run:
    """A results file: what the suite measured, and what measured it."""

    overall: dict[str, float]
    by_slice: dict[str, dict[str, float]]
    instrument: dict[str, str]

    @classmethod
    def load(cls, path: str | Path) -> Run:
        raw = json.loads(Path(path).read_text())
        return cls(
            overall=raw["overall"],
            by_slice=raw.get("by_slice", {}),
            instrument=raw.get("instrument", {}),
        )


def check_bars(run: Run, bars: dict[str, float] = BARS) -> list[str]:
    return [
        f"{metric} {run.overall[metric]:.3f} is below the bar of {bar:.2f}"
        for metric, bar in bars.items()
        if metric in run.overall and run.overall[metric] < bar
    ]


def check_instrument(run: Run, baseline: Run) -> list[str]:
    """A score is only comparable to a score taken with the same instrument."""
    changed = [
        f"{key}: {baseline.instrument[key]!r} -> {run.instrument.get(key)!r}"
        for key in sorted(baseline.instrument)
        if run.instrument.get(key) != baseline.instrument[key]
    ]
    if not changed:
        return []
    return [
        "the instrument changed, so these numbers are not comparable "
        f"({'; '.join(changed)}) — re-baseline deliberately, in a reviewed commit"
    ]


def check_regressions(
    run: Run, baseline: Run, tolerance: float = TOLERANCE
) -> list[str]:
    problems = [
        f"{metric} regressed {baseline.overall[metric]:.3f} -> {run.overall[metric]:.3f} "
        f"(tolerance {tolerance:.2f})"
        for metric in sorted(baseline.overall)
        if metric in run.overall
        and run.overall[metric] < baseline.overall[metric] - tolerance
    ]

    for name, base_scores in sorted(baseline.by_slice.items()):
        if name not in run.by_slice:
            problems.append(f"slice '{name}' disappeared from the results")
            continue
        for metric, base in sorted(base_scores.items()):
            now = run.by_slice[name].get(metric)
            if now is None:
                problems.append(f"slice '{name}' no longer reports {metric}")
            elif now < base - tolerance:
                problems.append(
                    f"slice '{name}' {metric} regressed {base:.3f} -> {now:.3f}"
                    + (" — COLLAPSED" if now < COLLAPSE_FLOOR <= base else "")
                )
    return problems


def gate(run: Run, baseline: Run, tolerance: float = TOLERANCE) -> list[str]:
    """Every reason to block the merge. Empty list means it may land."""
    return (
        check_instrument(run, baseline)
        + check_bars(run)
        + check_regressions(run, baseline, tolerance)
    )


def diff_table(run: Run, baseline: Run, tolerance: float = TOLERANCE) -> str:
    """The receipt. A failing gate is a code-review artifact, not a stack trace."""
    rows: list[tuple[str, str, float, float]] = [
        (f"OVERALL {metric}", metric, baseline.overall.get(metric, 0.0), value)
        for metric, value in sorted(run.overall.items())
    ]
    rows += [
        (f"{name} {metric}", metric, baseline.by_slice.get(name, {}).get(metric, 0.0), value)
        for name, scores in sorted(run.by_slice.items())
        for metric, value in sorted(scores.items())
    ]

    header = f"{'metric':<34}{'base':>8}{'now':>8}{'delta':>8}   status"
    lines = [header, "-" * len(header)]
    for label, _metric, base, now in rows:
        delta = now - base
        if now < base - tolerance:
            status = "REGRESSED"
        elif delta < 0:
            status = "ok (within tolerance)"
        else:
            status = "ok"
        lines.append(f"{label:<34}{base:>8.3f}{now:>8.3f}{delta:>+8.3f}   {status}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if len(args) != 2:
        print("usage: python -m src.gate RESULTS.json BASELINE.json", file=sys.stderr)
        return 2

    run, baseline = Run.load(args[0]), Run.load(args[1])
    print(diff_table(run, baseline))
    problems = gate(run, baseline)
    if not problems:
        print("\ngate passed")
        return 0
    print("\ngate FAILED:")
    for problem in problems:
        print(f"  - {problem}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
