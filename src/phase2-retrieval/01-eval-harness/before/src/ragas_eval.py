"""TODO (tier 2): the REAL RAGAS evaluation.

    from ragas import EvaluationDataset, evaluate
    from ragas.dataset_schema import SingleTurnSample
    from ragas.metrics import Faithfulness, LLMContextRecall
    from ragas.llms import LangchainLLMWrapper
    from langchain_openai import ChatOpenAI

- local_judge(): a FREE judge on Ollama (base_url=http://localhost:11434/v1),
  temperature=0. PIN IT — the judge is part of the ruler.
- run_ragas(golden, pipeline, judge): build SingleTurnSamples, evaluate, return scores.
- gate(scores): fail under faithfulness 0.85 / context_recall 0.80.

Run with: make test-integration     Reference: ../after/src/ragas_eval.py
"""
from __future__ import annotations

from collections.abc import Callable

FAITHFULNESS_BAR = 0.85
CONTEXT_RECALL_BAR = 0.80


def local_judge(model: str = "qwen3-coder:30b"):
    raise NotImplementedError  # TODO 1


def run_ragas(
    golden: list[dict],
    pipeline: Callable[[str], tuple[str, list[str]]],
    judge=None,
) -> dict:
    raise NotImplementedError  # TODO 2


def gate(scores: dict) -> tuple[bool, list[str]]:
    raise NotImplementedError  # TODO 3
