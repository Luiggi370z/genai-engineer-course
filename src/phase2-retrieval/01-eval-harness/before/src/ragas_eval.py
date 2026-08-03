"""TODO (tier 2): the REAL RAGAS evaluation.

    from openai import AsyncOpenAI
    from ragas.llms import llm_factory
    from ragas.metrics.collections import ContextRecall, Faithfulness

Verified against **ragas 0.4.3** (2026-07-31). The metric classes live in
`ragas.metrics.collections` and take a judge built by `llm_factory` over an
`AsyncOpenAI` client. If a tutorial hands you `from ragas.metrics import
Faithfulness` with `evaluate()` and `EvaluationDataset`, that is the pre-0.4
surface: it still imports, it raises a DeprecationWarning, and it will not match
what lesson 3.2 teaches. Metrics score ONE sample at a time via `score(...)`, so
you average across the golden set yourself.

- local_judge(): a FREE judge on Ollama (base_url=http://localhost:11434/v1),
  temperature=0. PIN IT — the judge is part of the ruler.
- run_ragas(golden, pipeline, judge): score every row, return the means.
- gate(scores): fail under faithfulness 0.85 / context_recall 0.80.

Run with: make test-integration     Reference: ../after/src/ragas_eval.py
"""
from __future__ import annotations

from collections.abc import Callable

FAITHFULNESS_BAR = 0.85
CONTEXT_RECALL_BAR = 0.80

DEFAULT_LOCAL_MODEL = "qwen3-coder:30b"
DEFAULT_HOSTED_MODEL = "gpt-5.5"
OLLAMA_BASE_URL = "http://localhost:11434/v1"


def local_judge(model: str = DEFAULT_LOCAL_MODEL):
    raise NotImplementedError  # TODO 1


def hosted_judge(model: str = DEFAULT_HOSTED_MODEL):
    """A hosted judge (needs OPENAI_API_KEY). Stronger, costs tokens. Same
    `llm_factory` call as the local one with the base URL left off — which is
    the point: any Ollama model speaks the OpenAI API."""
    raise NotImplementedError  # TODO 1b


def run_ragas(
    golden: list[dict],
    pipeline: Callable[[str], tuple[str, list[str]]],
    judge=None,
) -> dict:
    raise NotImplementedError  # TODO 2


def describe(model: str = DEFAULT_LOCAL_MODEL) -> dict[str, str]:
    """A score without its instrument is not a measurement. Return the judge
    model, its temperature, and `importlib.metadata.version("ragas")` — the
    three things that make today's 0.91 comparable to last week's 0.88."""
    raise NotImplementedError  # TODO 3


def gate(scores: dict) -> tuple[bool, list[str]]:
    raise NotImplementedError  # TODO 4
