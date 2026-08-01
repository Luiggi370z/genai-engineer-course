"""The eval harness — everything except the judge itself, and therefore testable.

The design rule that makes this lesson work: **the judge is injected**. The harness
knows how to run a golden set, when a row needs a judge at all, how to aggregate
per slice, and what to record alongside the numbers. None of that needs a model, so
all of it is covered by `make test` — offline, deterministic, free.

`src/ragas_judge.py` provides the real judge (RAGAS + a pinned local model) and is
exercised only by `make test-integration`.

Two decisions worth copying into your own repo:

  * **Abstention rows are scored without the judge.** "Did the system refuse?" is a
    string check. Asking an LLM to grade it adds cost, latency and noise to the one
    slice you least want noise in.
  * **Aggregate per slice, always.** An overall mean of 0.86 can hide the
    unanswerable slice collapsing from 1.00 to 0.40. Averages are where regressions
    go to hide.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Protocol

METRICS = ("faithfulness", "context_recall")

# Phrases that count as an honest "I don't know". Keep this list in ONE place:
# the system, the harness and the workshop all have to agree on what abstaining
# looks like, or you will grade a refusal as a hallucination.
ABSTENTION_MARKERS = (
    "not in the docs",
    "not in the documents",
    "i don't know",
    "i do not know",
    "no information",
    "cannot answer",
    "can't answer",
)


class Judge(Protocol):
    """The only component allowed to need a model."""

    def faithfulness(self, question: str, answer: str, contexts: list[str]) -> float: ...

    def context_recall(self, question: str, contexts: list[str], reference: str) -> float: ...

    def describe(self) -> dict[str, str]:
        """Model, temperature, library version — the instrument, recorded with the score."""
        ...


Pipeline = Callable[[str], tuple[str, list[str]]]


@dataclass(frozen=True)
class Row:
    id: str
    slice: str
    question: str
    ground_truth: str
    expects_abstention: bool = False
    supporting_doc_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ScoredRow:
    id: str
    slice: str
    scores: dict[str, float]
    judged: bool


@dataclass(frozen=True)
class SuiteResult:
    overall: dict[str, float]
    by_slice: dict[str, dict[str, float]]
    rows: list[ScoredRow]
    instrument: dict[str, str]

    def to_json(self) -> str:
        return json.dumps(
            {
                "overall": self.overall,
                "by_slice": self.by_slice,
                "instrument": self.instrument,
                "rows": [asdict(r) for r in self.rows],
            },
            indent=2,
            sort_keys=True,
        )


def load_golden(path: str | Path) -> list[Row]:
    return [
        Row(
            id=r["id"],
            slice=r["slice"],
            question=r["question"],
            ground_truth=r["ground_truth"],
            expects_abstention=r.get("expects_abstention", False),
            supporting_doc_ids=r.get("supporting_doc_ids", []),
        )
        for r in (
            json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()
        )
    ]


def is_abstention(answer: str) -> bool:
    lowered = answer.lower()
    return any(marker in lowered for marker in ABSTENTION_MARKERS)


def score_row(row: Row, answer: str, contexts: list[str], judge: Judge) -> ScoredRow:
    """One row, scored. Abstention rows never reach the judge."""
    if row.expects_abstention:
        refused = float(is_abstention(answer))
        return ScoredRow(row.id, row.slice, dict.fromkeys(METRICS, refused), judged=False)
    return ScoredRow(
        row.id,
        row.slice,
        {
            "faithfulness": judge.faithfulness(row.question, answer, contexts),
            "context_recall": judge.context_recall(row.question, contexts, row.ground_truth),
        },
        judged=True,
    )


def mean_scores(rows: Iterable[ScoredRow]) -> dict[str, float]:
    rows = list(rows)
    if not rows:
        return dict.fromkeys(METRICS, 0.0)
    return {
        metric: round(sum(r.scores[metric] for r in rows) / len(rows), 3) for metric in METRICS
    }


def run_suite(rows: list[Row], pipeline: Pipeline, judge: Judge) -> SuiteResult:
    scored = [score_row(row, *pipeline(row.question), judge) for row in rows]
    slices = sorted({r.slice for r in scored})
    return SuiteResult(
        overall=mean_scores(scored),
        by_slice={s: mean_scores(r for r in scored if r.slice == s) for s in slices},
        rows=scored,
        instrument=judge.describe(),
    )


def format_table(result: SuiteResult) -> str:
    """The per-slice view. Read this, not the overall number."""
    header = f"{'slice':<14}" + "".join(f"{m:>16}" for m in METRICS) + f"{'rows':>7}"
    lines = [header, "-" * len(header)]
    for name, scores in result.by_slice.items():
        n = sum(r.slice == name for r in result.rows)
        lines.append(f"{name:<14}" + "".join(f"{scores[m]:>16.3f}" for m in METRICS) + f"{n:>7}")
    lines.append("-" * len(header))
    lines.append(
        f"{'OVERALL':<14}"
        + "".join(f"{result.overall[m]:>16.3f}" for m in METRICS)
        + f"{len(result.rows):>7}"
    )
    judged = sum(r.judged for r in result.rows)
    lines.append(f"judged rows: {judged}/{len(result.rows)}  instrument: {result.instrument}")
    return "\n".join(lines)
