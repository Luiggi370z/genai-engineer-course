"""A RAG eval harness with TWO tiers, because that's how real teams run evals.

Tier 1 — `make test` (this module): deterministic, offline, free. Non-LLM metrics
computed with `rapidfuzz`. These mirror RAGAS's own NonLLM* metric family
(NonLLMContextRecall, NonLLMStringSimilarity) and are honest about what they
measure: string similarity, NOT semantic faithfulness. Fast enough for every PR.

Tier 2 — `make test-integration` (src/ragas_eval.py): the real RAGAS metrics with
a pinned LLM judge. Slower, costs tokens (or runs free on Ollama). Nightly / pre-merge.

Never pretend tier 1 is tier 2. Naming your metrics honestly is part of the job.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from rapidfuzz import fuzz


@dataclass
class Row:
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str


def load_golden(path: str | Path) -> list[dict]:
    """Read a jsonl golden set: {"question", "ground_truth"} per line."""
    return [
        json.loads(line)
        for line in Path(path).read_text().splitlines()
        if line.strip()
    ]


# ----------------------------------------------------- tier 1: non-LLM (offline)
def answer_similarity_nonllm(row: Row) -> float:
    """How close is the answer to the reference, as a STRING? 0..1 (rapidfuzz)."""
    return fuzz.token_set_ratio(row.answer, row.ground_truth) / 100.0


def context_recall_nonllm(row: Row) -> float:
    """Did retrieval surface text resembling the reference? 0..1 (rapidfuzz).

    RAGAS calls this family NonLLMContextRecall — same idea: compare retrieved
    contexts to reference contexts lexically, no judge model required.
    """
    if not row.contexts:
        return 0.0
    return max(fuzz.token_set_ratio(c, row.ground_truth) for c in row.contexts) / 100.0


def evaluate_nonllm(rows: list[Row]) -> dict[str, float]:
    """Averages for the fast gate. Honest names: these are lexical, not semantic."""
    if not rows:
        return {"answer_similarity_nonllm": 0.0, "context_recall_nonllm": 0.0}
    n = len(rows)
    return {
        "answer_similarity_nonllm": round(
            sum(answer_similarity_nonllm(r) for r in rows) / n, 3),
        "context_recall_nonllm": round(
            sum(context_recall_nonllm(r) for r in rows) / n, 3),
    }


def build_dataset(
    golden: list[dict],
    pipeline: Callable[[str], tuple[str, list[str]]],
) -> list[Row]:
    """Run each golden question through YOUR rag pipeline; collect answer + contexts."""
    return [
        Row(ex["question"], *pipeline(ex["question"]), ex["ground_truth"])
        for ex in golden
    ]
