"""The real judge: RAGAS metrics driven by a pinned model. Opt-in tier.

    make test-integration          # needs Ollama running
    uv run --group integration python -m src.ragas_judge

API note, verified against **ragas 0.4.3** (2026-07-31): the current metric classes
live in `ragas.metrics.collections` and take an explicit judge built by
`ragas.llms.llm_factory`. The older `from ragas.metrics import Faithfulness` path
still imports but now raises a DeprecationWarning pointing here, and `evaluate()`
plus `EvaluationDataset` belong to that older surface. Metric instances expose both
`ascore(...)` and a synchronous `score(...)`.

Pinning, in order of how often it bites:

  1. **The judge model.** It is part of the ruler. Model + temperature 0, recorded
     next to every score. Swap it silently and your dashboard moves on its own.
  2. **The generator must not be the judge.** Models favour their own family's
     writing; grading your own homework is exactly as reliable as it sounds.
  3. **The dependency tree.** RAGAS wraps LangChain, which moves fast. Pin
     `ragas` narrowly and upgrade it deliberately — this is why the whole judged
     tier is an optional dependency group instead of part of `make test`.
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_MODEL = "qwen3-coder:30b"
OLLAMA_BASE_URL = "http://localhost:11434/v1"


@dataclass
class RagasJudge:
    """Implements the harness's `Judge` protocol with real RAGAS metrics.

    Free by default: any Ollama model speaks the OpenAI API, so the same code path
    serves a local judge and a hosted one. Calibrate the local judge against your
    own labels (lesson 3.3) before you trust it to gate merges.
    """

    model: str = DEFAULT_MODEL
    base_url: str | None = OLLAMA_BASE_URL
    temperature: float = 0.0

    def __post_init__(self) -> None:
        from openai import AsyncOpenAI
        from ragas.llms import llm_factory
        from ragas.metrics.collections import ContextRecall, Faithfulness

        client = (
            AsyncOpenAI(base_url=self.base_url, api_key="ollama")
            if self.base_url
            else AsyncOpenAI()  # hosted: OPENAI_API_KEY from the environment
        )
        judge = llm_factory(self.model, client=client, temperature=self.temperature)
        self._faithfulness = Faithfulness(llm=judge)
        self._context_recall = ContextRecall(llm=judge)

    def faithfulness(self, question: str, answer: str, contexts: list[str]) -> float:
        result = self._faithfulness.score(
            user_input=question, response=answer, retrieved_contexts=contexts
        )
        return float(result.value)

    def context_recall(self, question: str, contexts: list[str], reference: str) -> float:
        result = self._context_recall.score(
            user_input=question, retrieved_contexts=contexts, reference=reference
        )
        return float(result.value)

    def describe(self) -> dict[str, str]:
        """A score without its instrument is not a measurement."""
        from importlib.metadata import version

        return {
            "judge_model": self.model,
            "judge_temperature": str(self.temperature),
            "judge_endpoint": self.base_url or "hosted",
            "ragas_version": version("ragas"),
        }


if __name__ == "__main__":
    from src.harness import format_table, load_golden, run_suite

    # Stand-in pipeline: swap in your Workshop-2 service.
    def pipeline(question: str) -> tuple[str, list[str]]:
        return "Not in the documents.", []

    result = run_suite(load_golden("evals/golden.jsonl")[:3], pipeline, RagasJudge())
    print(format_table(result))
