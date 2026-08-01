"""The golden set, treated as a piece of engineering instead of a text file.

Every eval number you quote is a property of THIS dataset, so the dataset gets
tests of its own — before you trust a single score computed from it:

  * every slice populated                  (a missing slice is a blind spot)
  * enough unanswerable rows               (or the abstain path is untested)
  * no near-duplicate questions            (accidental copy-paste inflates a slice)
  * no question lifted out of a chunk      (that measures string matching, not retrieval)
  * provenance on every row                (a row that can't justify itself gets cut)

`rapidfuzz` does the string work: `token_set_ratio` for "same question, different
words", `partial_ratio` for "this question is a substring of that chunk". Both go
through `default_process` — without it, a capital letter or a comma is enough to
drop a true duplicate under the threshold.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from rapidfuzz import fuzz
from rapidfuzz.utils import default_process

SLICES = ("semantic", "exact", "multi_hop", "unanswerable", "adversarial")

MIN_UNANSWERABLE = 5
DUPLICATE_THRESHOLD = 92.0
LEAKAGE_THRESHOLD = 95.0


@dataclass(frozen=True)
class GoldenRow:
    id: str
    slice: str
    question: str
    ground_truth: str
    expects_abstention: bool = False
    supporting_doc_ids: list[str] = field(default_factory=list)
    source: str = ""
    labeled_by: str = ""
    labeled_on: str = ""


def load_golden(path: str | Path) -> list[GoldenRow]:
    """Read a jsonl golden set. Unknown keys are a typo, not a feature — so they raise."""
    rows = [
        GoldenRow(**json.loads(line))
        for line in Path(path).read_text().splitlines()
        if line.strip()
    ]
    if len({r.id for r in rows}) != len(rows):
        raise ValueError("duplicate row ids in the golden set")
    return rows


def load_corpus(path: str | Path) -> list[str]:
    """The chunks the system retrieves over — needed for the leakage check."""
    return [
        json.loads(line)["text"]
        for line in Path(path).read_text().splitlines()
        if line.strip()
    ]


def near_duplicates(
    rows: list[GoldenRow], threshold: float = DUPLICATE_THRESHOLD
) -> list[tuple[str, str]]:
    """Pairs of questions that are the same question wearing different words."""
    pairs = []
    for i, a in enumerate(rows):
        for b in rows[i + 1 :]:
            if fuzz.token_set_ratio(a.question, b.question, processor=default_process) >= threshold:
                pairs.append((a.id, b.id))
    return pairs


def leaked_questions(
    rows: list[GoldenRow], chunks: list[str], threshold: float = LEAKAGE_THRESHOLD
) -> list[str]:
    """Rows whose question is copy-pasted out of a chunk.

    Those rows score well for the wrong reason: the retriever is matching the
    question's own source text, so you are measuring string overlap and calling
    it retrieval quality.
    """
    return [
        r.id
        for r in rows
        if any(
            fuzz.partial_ratio(r.question, c, processor=default_process) >= threshold
            for c in chunks
        )
    ]


def slice_counts(rows: list[GoldenRow]) -> dict[str, int]:
    return {s: sum(r.slice == s for r in rows) for s in SLICES}


def missing_provenance(rows: list[GoldenRow]) -> list[str]:
    """A row with no source and no labeller is a row nobody can defend in review."""
    return [r.id for r in rows if not (r.source and r.labeled_by and r.labeled_on)]


def unsupported_answerable(rows: list[GoldenRow]) -> list[str]:
    """Answerable rows must name the docs that support them.

    That single field is what lets you compute retrieval metrics with no judge:
    "did the supporting doc show up in the top-k?" is a set membership test.
    """
    return [
        r.id for r in rows if not r.expects_abstention and not r.supporting_doc_ids
    ]


def validate(rows: list[GoldenRow], chunks: list[str]) -> list[str]:
    """Every problem worth blocking a merge over, as human-readable strings."""
    problems: list[str] = []

    counts = slice_counts(rows)
    problems += [f"slice '{s}' is empty" for s, n in counts.items() if n == 0]

    unanswerable = sum(r.expects_abstention for r in rows)
    if unanswerable < MIN_UNANSWERABLE:
        problems.append(
            f"only {unanswerable} unanswerable rows (need >= {MIN_UNANSWERABLE}): "
            "the abstain path would go untested"
        )

    problems += [f"near-duplicate questions: {a} ~ {b}" for a, b in near_duplicates(rows)]
    problems += [f"question leaked from a chunk: {rid}" for rid in leaked_questions(rows, chunks)]
    problems += [f"missing provenance: {rid}" for rid in missing_provenance(rows)]
    problems += [
        f"answerable row without supporting_doc_ids: {rid}"
        for rid in unsupported_answerable(rows)
    ]

    for r in rows:
        if r.slice not in SLICES:
            problems.append(f"unknown slice '{r.slice}' on {r.id}")
        if r.expects_abstention != (r.slice == "unanswerable"):
            problems.append(
                f"{r.id}: expects_abstention and slice 'unanswerable' must agree"
            )

    return problems


def report(rows: list[GoldenRow], chunks: list[str]) -> str:
    """What you paste into the PR that grows the golden set."""
    counts = slice_counts(rows)
    lines = [f"{len(rows)} rows"]
    lines += [f"  {s:<13} {n:>3}" for s, n in counts.items()]
    problems = validate(rows, chunks)
    lines.append("  OK" if not problems else "  PROBLEMS:")
    lines += [f"   - {p}" for p in problems]
    return "\n".join(lines)


if __name__ == "__main__":
    print(report(load_golden("evals/golden.jsonl"), load_corpus("evals/corpus.jsonl")))
