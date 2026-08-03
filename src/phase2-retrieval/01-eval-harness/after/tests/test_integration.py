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


def test_the_installed_ragas_is_the_one_this_lesson_was_written_against():
    """A pin in a pyproject is an intention; this is the check.

    RAGAS moved its metric classes into `ragas.metrics.collections` at 0.4 and
    left the old import path importable with a DeprecationWarning — so code
    written against the old surface keeps working long enough to be copied,
    and then diverges from what lesson 3.2 teaches. Fail loudly instead."""
    from importlib.metadata import version

    from ragas.llms import llm_factory  # noqa: F401  (the 0.4 judge builder)
    from ragas.metrics.collections import ContextRecall, Faithfulness  # noqa: F401

    major, minor, *_ = version("ragas").split(".")
    assert (int(major), int(minor)) == (0, 4), (
        f"this lesson is written against ragas 0.4.x, found {version('ragas')}"
    )


def test_the_scores_travel_with_the_instrument_that_produced_them():
    """A number without its judge is not comparable to next week's number."""
    from src.ragas_eval import describe

    stamp = describe()
    assert stamp["judge_temperature"] == "0.0"
    assert stamp["judge_model"] and stamp["ragas_version"]
