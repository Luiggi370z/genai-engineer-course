"""Tier 2 — the REAL RAGAS evaluation with a pinned LLM judge.

This is what you report in your README and gate merges on nightly. Run it with:

    make test-integration          # or: uv run --group integration python -m src.ragas_eval

Two things that bite people:
  1. **Pin the judge** (model + temperature 0). The judge is part of the ruler; an
     unpinned judge means today's 0.91 isn't comparable to last week's 0.88.
  2. RAGAS has a heavy, fast-moving dependency tree (it wraps LangChain). Pin
     `ragas` and `langchain-*` together and upgrade them deliberately.
"""
from __future__ import annotations

from collections.abc import Callable

FAITHFULNESS_BAR = 0.85
CONTEXT_RECALL_BAR = 0.80


def local_judge(model: str = "qwen3-coder:30b"):
    """A FREE judge on Ollama. Validate it against a hosted judge once, then reuse."""
    from langchain_openai import ChatOpenAI
    from ragas.llms import LangchainLLMWrapper

    return LangchainLLMWrapper(
        ChatOpenAI(
            model=model,
            temperature=0,  # pin it
            base_url="http://localhost:11434/v1",
            api_key="ollama",
        )
    )


def hosted_judge(model: str = "gpt-5.5"):
    """A hosted judge (needs OPENAI_API_KEY). Stronger, costs tokens."""
    from langchain_openai import ChatOpenAI
    from ragas.llms import LangchainLLMWrapper

    return LangchainLLMWrapper(ChatOpenAI(model=model, temperature=0))


def run_ragas(
    golden: list[dict],
    pipeline: Callable[[str], tuple[str, list[str]]],
    judge=None,
) -> dict:
    """Score a golden set with the real RAGAS metrics."""
    from ragas import EvaluationDataset, evaluate
    from ragas.dataset_schema import SingleTurnSample
    from ragas.metrics import Faithfulness, LLMContextRecall

    judge = judge or local_judge()
    samples = []
    for ex in golden:
        answer, contexts = pipeline(ex["question"])
        samples.append(
            SingleTurnSample(
                user_input=ex["question"],
                response=answer,
                retrieved_contexts=contexts,
                reference=ex["ground_truth"],
            )
        )
    result = evaluate(
        EvaluationDataset(samples=samples),
        metrics=[Faithfulness(llm=judge), LLMContextRecall(llm=judge)],
    )
    return dict(result)


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
