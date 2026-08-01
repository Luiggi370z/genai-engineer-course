"""TODO: build the two-tier eval harness. Use libraries; don't invent metrics.

Tier 1 (this file) — deterministic, offline, every PR. Use `rapidfuzz` for
non-LLM string metrics. Name them honestly: they measure lexical similarity,
NOT semantic faithfulness. (RAGAS calls this family NonLLM*.)

Tier 2 — src/ragas_eval.py: the real RAGAS metrics with a pinned LLM judge.

    from rapidfuzz import fuzz
    fuzz.token_set_ratio(a, b)   # 0..100, order-insensitive

Reference: ../after/src/harness.py
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Row:
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str


def load_golden(path: str | Path) -> list[dict]:
    """TODO 1: read the jsonl golden set."""
    raise NotImplementedError


def answer_similarity_nonllm(row: Row) -> float:
    """TODO 2: rapidfuzz token_set_ratio(answer, ground_truth) scaled to 0..1."""
    raise NotImplementedError


def context_recall_nonllm(row: Row) -> float:
    """TODO 3: best rapidfuzz score between any retrieved context and ground_truth."""
    raise NotImplementedError


def evaluate_nonllm(rows: list[Row]) -> dict[str, float]:
    """TODO 4: average both metrics across rows."""
    raise NotImplementedError


def build_dataset(
    golden: list[dict],
    pipeline: Callable[[str], tuple[str, list[str]]],
) -> list[Row]:
    """TODO 5: run each question through the pipeline, collect answer + contexts."""
    raise NotImplementedError
