"""Tier 2 — the REAL RAGAS evaluation with a pinned LLM judge.

This is what you report in your README and gate merges on nightly. Run it with:

    make test-integration          # or: uv run --group integration python -m src.ragas_eval

API note, verified against **ragas 0.4.3** (2026-07-31): the metric classes live
in `ragas.metrics.collections` and take an explicit judge built by
`ragas.llms.llm_factory` over an `openai.AsyncOpenAI` client. The older
`from ragas.metrics import Faithfulness` path still imports but raises a
DeprecationWarning pointing here, and `evaluate()` plus `EvaluationDataset`
belong to that older surface. Metric instances expose `ascore(...)` and a
synchronous `score(...)`, one sample at a time — which is why the loop below is
explicit rather than a single `evaluate()` call.

Lesson 3.2 uses this same surface, deliberately: two lessons teaching two RAGAS
APIs is the course arguing with itself, and the reader has no way to tell which
half is current. `check-claims` now fails the build if the pins drift apart.

Two things that bite people:
  1. **Pin the judge** (model + temperature 0). The judge is part of the ruler; an
     unpinned judge means today's 0.91 isn't comparable to last week's 0.88.
  2. RAGAS moves fast. Pin it narrowly and upgrade it deliberately — which is why
     this whole tier sits in an optional dependency group.
"""
from __future__ import annotations

from collections.abc import Callable

FAITHFULNESS_BAR = 0.85
CONTEXT_RECALL_BAR = 0.80

DEFAULT_LOCAL_MODEL = "qwen3-coder:30b"
DEFAULT_HOSTED_MODEL = "gpt-5.5"
OLLAMA_BASE_URL = "http://localhost:11434/v1"


def local_judge(model: str = DEFAULT_LOCAL_MODEL):
    """A FREE judge on Ollama. Validate it against a hosted judge once, then reuse.

    Any Ollama model speaks the OpenAI API, so the local and hosted paths differ
    by a base URL and nothing else.
    """
    from openai import AsyncOpenAI
    from ragas.llms import llm_factory

    client = AsyncOpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
    return llm_factory(model, client=client, temperature=0)  # pin it


def hosted_judge(model: str = DEFAULT_HOSTED_MODEL):
    """A hosted judge (needs OPENAI_API_KEY). Stronger, costs tokens."""
    from openai import AsyncOpenAI
    from ragas.llms import llm_factory

    return llm_factory(model, client=AsyncOpenAI(), temperature=0)


def run_ragas(
    golden: list[dict],
    pipeline: Callable[[str], tuple[str, list[str]]],
    judge=None,
) -> dict:
    """Score a golden set with the real RAGAS metrics.

    Averaged over the rows, because a per-row score is a diagnosis and a merge
    gate needs a number. Keep the per-row values when you are debugging a
    regression — the mean tells you something moved, never which row.
    """
    from ragas.metrics.collections import ContextRecall, Faithfulness

    judge = judge or local_judge()
    faithfulness, context_recall = Faithfulness(llm=judge), ContextRecall(llm=judge)

    scored: list[tuple[float, float]] = []
    for ex in golden:
        answer, contexts = pipeline(ex["question"])
        scored.append((
            float(faithfulness.score(
                user_input=ex["question"], response=answer, retrieved_contexts=contexts
            ).value),
            float(context_recall.score(
                user_input=ex["question"], retrieved_contexts=contexts,
                reference=ex["ground_truth"],
            ).value),
        ))

    if not scored:
        return {"faithfulness": 0.0, "context_recall": 0.0}
    return {
        "faithfulness": sum(f for f, _ in scored) / len(scored),
        "context_recall": sum(c for _, c in scored) / len(scored),
    }


def describe(model: str = DEFAULT_LOCAL_MODEL) -> dict[str, str]:
    """A score without its instrument is not a measurement. Report this beside
    every number you publish."""
    from importlib.metadata import version

    return {
        "judge_model": model,
        "judge_temperature": "0.0",
        "ragas_version": version("ragas"),
    }


def gate(scores: dict) -> tuple[bool, list[str]]:
    """Merge gate on the REAL metrics."""
    reasons = []
    f = scores.get("faithfulness", 0.0)
    c = scores.get("context_recall", 0.0)
    if f < FAITHFULNESS_BAR:
        reasons.append(f"faithfulness {f:.2f} < {FAITHFULNESS_BAR}")
    if c < CONTEXT_RECALL_BAR:
        reasons.append(f"context_recall {c:.2f} < {CONTEXT_RECALL_BAR}")
    return not reasons, reasons
