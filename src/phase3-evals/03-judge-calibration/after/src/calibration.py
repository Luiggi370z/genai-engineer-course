"""Calibration: measuring how much your judge deserves to be trusted.

The question this module answers is the one that separates people who run evals
from people who trust them: **how do you know the judge is right?** The only honest
answer is that you labeled some rows yourself and measured the overlap.

Two numbers, and only one of them is safe to report alone:

  * **agreement** — the share of rows where the judge said what you said. Easy to
    read, and a liar whenever the classes are imbalanced: with 90% passes, a judge
    that always says "pass" scores 0.90 and has learned nothing.
  * **Cohen's kappa** — the same overlap, corrected for the agreement you would get
    by chance. This is the number that belongs next to your scores.

`sklearn.metrics.cohen_kappa_score` does the arithmetic; the judgement calls (which
threshold, how much tolerance, whether to gate at all) are yours, and they are the
actual skill.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from math import sqrt
from pathlib import Path

from sklearn.metrics import cohen_kappa_score

LABELS = ("pass", "fail")

# Landis & Koch's long-standing bands for inter-rater agreement. A convention for
# deciding how much to trust a second rater — not a law of nature, and not a target
# to congratulate yourself against.
BANDS = (
    (0.20, "the judge is measuring something else entirely — rewrite the rubric"),
    (0.40, "weak signal: fine for smoke tests, not for gating merges"),
    (0.60, "usable with a margin — gate on regressions, not on absolutes"),
    (1.01, "substantial agreement — you can defend gating merges on this"),
)

# Below this, treating the judge as a merge gate is not defensible.
GATING_KAPPA = 0.60


@dataclass(frozen=True)
class LabeledRow:
    """One row you looked at with your own eyes, plus what the judge said."""

    id: str
    question: str
    answer: str
    judge_score: float
    human: str
    labeled_by: str = ""
    labeled_on: str = ""


@dataclass(frozen=True)
class Calibration:
    n: int
    threshold: float
    agreement: float
    kappa: float
    disagreements: list[str]
    judge_pass_rate: float
    human_pass_rate: float

    @property
    def gatable(self) -> bool:
        return self.kappa >= GATING_KAPPA

    @property
    def tolerance(self) -> float:
        """The smallest *suite-level* move worth failing CI over.

        Your judge disagrees with you on `1 - agreement` of rows. Averaged over n
        rows, that per-row noise shrinks like `disagreement / sqrt(n)` — so a move
        in the aggregate smaller than this is indistinguishable from the judge
        having a different opinion than you on a couple of rows.

        Gate wider than this number. A gate that fires on noise gets routed around,
        and a routed-around gate is worse than no gate: it looks like coverage.
        """
        return round(max((1.0 - self.agreement) / sqrt(self.n), 0.01), 2)


def load_labeled(path: str | Path) -> list[LabeledRow]:
    rows = [
        LabeledRow(**json.loads(line))
        for line in Path(path).read_text().splitlines()
        if line.strip()
    ]
    unknown = {r.human for r in rows} - set(LABELS)
    if unknown:
        raise ValueError(f"unknown human labels: {sorted(unknown)}")
    return rows


def verdicts(rows: list[LabeledRow], threshold: float) -> list[str]:
    """Turn the judge's numeric score into the same vocabulary you labeled in."""
    return ["pass" if r.judge_score >= threshold else "fail" for r in rows]


def calibrate(rows: list[LabeledRow], threshold: float = 0.5) -> Calibration:
    human = [r.human for r in rows]
    judge = verdicts(rows, threshold)
    return Calibration(
        n=len(rows),
        threshold=threshold,
        agreement=round(sum(h == j for h, j in zip(human, judge, strict=True)) / len(rows), 3),
        kappa=round(float(cohen_kappa_score(human, judge, labels=list(LABELS))), 3),
        disagreements=[r.id for r, j in zip(rows, judge, strict=True) if r.human != j],
        judge_pass_rate=round(judge.count("pass") / len(rows), 3),
        human_pass_rate=round(human.count("pass") / len(rows), 3),
    )


def best_threshold(rows: list[LabeledRow], step: float = 0.05) -> Calibration:
    """Pick the cut point from your labels instead of defaulting to 0.5.

    0.5 is a round number, not a decision. Sweeping costs nothing — the judge has
    already scored every row.
    """
    candidates = [round(step * i, 4) for i in range(1, int(1 / step))]
    return max(
        (calibrate(rows, t) for t in candidates),
        key=lambda c: (c.kappa, c.agreement),
    )


def interpret(kappa: float) -> str:
    return next(advice for edge, advice in BANDS if kappa < edge)


def disagreement_rows(rows: list[LabeledRow], calibration: Calibration) -> list[LabeledRow]:
    """The actual deliverable of a calibration run.

    Every disagreement is one of three things: a bad rubric, a bad label, or a
    question too ambiguous to belong in the golden set. Reading them is the work;
    the kappa is just the receipt.
    """
    ids = set(calibration.disagreements)
    return [r for r in rows if r.id in ids]


def report(rows: list[LabeledRow]) -> str:
    default = calibrate(rows)
    best = best_threshold(rows)
    lines = [
        f"{len(rows)} hand-labeled rows  "
        f"(human pass rate {default.human_pass_rate:.2f})",
        "",
        f"{'threshold':<12}{'agreement':>11}{'kappa':>8}{'judge pass rate':>18}",
        "-" * 49,
        f"{default.threshold:<12.2f}{default.agreement:>11.3f}"
        f"{default.kappa:>8.3f}{default.judge_pass_rate:>18.3f}   (default)",
        f"{best.threshold:<12.2f}{best.agreement:>11.3f}"
        f"{best.kappa:>8.3f}{best.judge_pass_rate:>18.3f}   (best kappa)",
        "",
        f"verdict: {interpret(best.kappa)}",
        f"gate on this judge? {'yes' if best.gatable else 'no'}   "
        f"regression tolerance: {best.tolerance:.2f}",
        f"disagreements to read: {', '.join(best.disagreements) or 'none'}",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    print(report(load_labeled("evals/labeled.jsonl")))
