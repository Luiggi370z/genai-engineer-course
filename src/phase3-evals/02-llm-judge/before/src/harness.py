"""TODO: build the harness so that everything EXCEPT the judge is testable offline.

The judge is injected (see the `Judge` protocol below). That one decision is what
lets `make test` cover the grading logic with no model, no key and no network — and
it is the difference between an eval suite you run on every push and one you run
when you remember to.

Two rules the tests will hold you to:

  * Abstention rows never reach the judge. "Did the system refuse?" is a string
    check; sending it to an LLM adds cost, latency and noise to the slice you least
    want noise in.
  * Aggregate per slice as well as overall. An overall 0.86 can hide the
    unanswerable slice at 0.40.

Reference: ../after/src/harness.py
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

METRICS = ("faithfulness", "context_recall")

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

    def describe(self) -> dict[str, str]: ...


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
        """TODO 7: serialize overall + by_slice + instrument + rows (`dataclasses.asdict`)."""
        raise NotImplementedError


def load_golden(path: str | Path) -> list[Row]:
    """TODO 1: read evals/golden.jsonl into Rows (you will want `json`)."""
    raise NotImplementedError


def is_abstention(answer: str) -> bool:
    """TODO 2: does the answer contain any ABSTENTION_MARKERS? (case-insensitive)"""
    raise NotImplementedError


def score_row(row: Row, answer: str, contexts: list[str], judge: Judge) -> ScoredRow:
    """TODO 3: score one row.

    Abstention rows: 1.0 on every metric if the system refused, 0.0 if it invented
    an answer — and `judged=False`, because the judge was never called.
    Everything else: ask the judge, `judged=True`.
    """
    raise NotImplementedError


def mean_scores(rows: Iterable[ScoredRow]) -> dict[str, float]:
    """TODO 4: mean per metric, rounded to 3 dp. An empty input is 0.0, not a crash."""
    raise NotImplementedError


def run_suite(rows: list[Row], pipeline: Pipeline, judge: Judge) -> SuiteResult:
    """TODO 5: score every row, then aggregate overall AND per slice.

    Record `judge.describe()` as the instrument — a score without its instrument is
    not a measurement.
    """
    raise NotImplementedError


def format_table(result: SuiteResult) -> str:
    """TODO 6: print one line per slice, then OVERALL, then the judged-row count."""
    raise NotImplementedError
