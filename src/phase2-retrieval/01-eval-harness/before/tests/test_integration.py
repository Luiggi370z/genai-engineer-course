"""Tier 2: the REAL RAGAS metrics with a pinned judge. Needs Ollama running.

    make test-integration
"""
import pytest

pytestmark = pytest.mark.integration

GOLDEN = "evals/golden.jsonl"


def _pipeline(q: str):
    from tests.test_quality import _pipeline as p

    return p(q)


def test_real_ragas_scores_and_gates():
    from src.harness import load_golden
    from src.ragas_eval import gate, run_ragas

    scores = run_ragas(load_golden(GOLDEN)[:3], _pipeline)
    assert "faithfulness" in scores
    ok, reasons = gate(scores)
    assert isinstance(ok, bool) and isinstance(reasons, list)
