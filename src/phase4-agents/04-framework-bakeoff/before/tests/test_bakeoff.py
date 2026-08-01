import pytest

from src.bakeoff import TypedAgent, Worker, crew_style, langgraph_style


def _answer(q: str) -> str:
    return f"answer to: {q}"


def test_all_three_produce_an_answer():
    assert langgraph_style("x", _answer) == "answer to: x"
    assert TypedAgent(_answer).run("x") == "answer to: x"
    out = crew_style("x", [Worker("w", _answer)])
    assert "answer to" in out


def test_pydantic_style_validates_input():
    with pytest.raises(ValueError):
        TypedAgent(_answer).run("")


def test_crew_passes_context_between_roles():
    workers = [Worker("a", lambda x: x + "-A"), Worker("b", lambda x: x + "-B")]
    assert crew_style("start", workers) == "start-A-B"
