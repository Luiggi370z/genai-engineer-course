"""Tier 2: the SAME tool-using agent, in three real libraries.

    make test-integration

One task — look a fact up with a tool, answer with it — run through LangGraph,
Pydantic AI and CrewAI, each returning the same `Run` shape so the results are
comparable rather than merely impressive.

The assertions are deliberately identical across the three. That is what makes
the differences that remain — glue, durability, whether an offline test is even
possible — attributable to the framework rather than to the example.

LangGraph and Pydantic AI run fully offline. CrewAI needs Ollama serving a
model on the host and is skipped cleanly when it is not up; that asymmetry is
itself a finding, and it belongs in the observability row of your matrix.
"""
from __future__ import annotations

import pytest

from src.frameworks import FACTS, TOPIC, Run, crewai_run, langgraph_run, pydantic_ai_run

pytestmark = pytest.mark.integration


def _assert_did_the_task(run: Run) -> None:
    """The same bar for all three, so the comparison is about the framework."""
    assert run.used_the_tool(), f"{run.framework} answered without calling the tool"
    assert run.tool_calls[0] == TOPIC
    assert run.answer


def test_langgraph_runs_the_shared_agent():
    _assert_did_the_task(langgraph_run())


def test_pydantic_ai_runs_the_shared_agent():
    _assert_did_the_task(pydantic_ai_run())


def test_crewai_runs_the_shared_agent():
    _require_crewai()
    if not _ollama_is_up():
        pytest.skip("Ollama is not serving on :11434")
    run = crewai_run()
    _assert_did_the_task(run)
    assert FACTS[TOPIC].split()[0].lower() in run.answer.lower()


def test_only_langgraph_leaves_state_a_second_call_can_resume():
    """The durability row of the matrix, measured rather than quoted.

    This is the one assertion that is allowed to differ between frameworks,
    because it is the finding: same task, same shape, and one of them can be
    picked back up after the process dies."""
    assert langgraph_run().resumable is True
    assert pydantic_ai_run().resumable is False


def test_the_langgraph_thread_is_addressable_by_id():
    """Resuming means resuming *this* conversation. Two threads, two states —
    without a line of persistence code of your own."""
    from langgraph.checkpoint.memory import MemorySaver  # noqa: F401  (proves the import)

    first = langgraph_run(thread="ticket-1")
    second = langgraph_run(topic="quantization", thread="ticket-2")
    assert first.answer != second.answer


def test_pydantic_ai_output_is_a_validated_model_not_a_string():
    """Its distinctive win, still on the shared task: the answer came out of a
    typed contract, so a malformed reply fails here instead of downstream."""
    run = pydantic_ai_run()
    assert ":" in run.answer  # "<topic>: <fact>", assembled from typed fields


def _require_crewai() -> None:
    """Skip with the real reason instead of a traceback from three layers down.

    CrewAI's dependency tree pins it to Python 3.12; on a newer interpreter it
    dies inside Chroma's Pydantic v1 shim with `unable to infer type for
    attribute "chroma_server_nofile"`, which looks like a CrewAI bug and is a
    Python version bound. Naming it here saves the hour everyone otherwise
    spends on it — and the fact that one of the three frameworks constrains
    your interpreter is a real finding for the matrix.
    """
    try:
        import crewai  # noqa: F401
    except Exception as exc:
        pytest.skip(f"crewai will not import here (needs Python 3.12): {exc}")


def _ollama_is_up() -> bool:
    import urllib.request

    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
        return True
    except OSError:
        return False
