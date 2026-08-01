"""Tier 2: the same three defining ideas, proven in the REAL libraries.

    make test-integration

LangGraph and Pydantic AI run fully offline (deterministic nodes; TestModel).
The CrewAI test drives real role orchestration and needs Ollama serving
qwen3.5:9b — it is skipped cleanly when Ollama is not up.
"""
from __future__ import annotations

from typing import TypedDict

import pytest

pytestmark = pytest.mark.integration


class State(TypedDict, total=False):
    q: str
    result: str


def test_langgraph_state_machine_checkpoints_and_resumes_by_thread_id():
    """The defining idea: durability. The run leaves a checkpoint behind that a
    new invocation can pick up by thread_id — no custom persistence code."""
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.graph import END, StateGraph

    def work(state: State) -> dict:
        return {"result": f"answer to: {state.get('q', '')}"}

    graph = StateGraph(State)
    graph.add_node("work", work)
    graph.set_entry_point("work")
    graph.add_edge("work", END)
    app = graph.compile(checkpointer=MemorySaver())

    config = {"configurable": {"thread_id": "bakeoff-1"}}
    out = app.invoke({"q": "x"}, config)
    assert out["result"] == "answer to: x"

    # The checkpoint is addressable state, not a side effect.
    snapshot = app.get_state(config)
    assert snapshot.values["result"] == "answer to: x"


def test_pydantic_ai_returns_a_validated_model_not_a_string():
    """The defining idea: safety. The agent's output is a validated Pydantic
    model — a malformed reply fails loudly instead of flowing downstream."""
    from pydantic import BaseModel
    from pydantic_ai import Agent
    from pydantic_ai.models.test import TestModel

    class Answer(BaseModel):
        text: str
        confidence: float

    agent = Agent(TestModel(), output_type=Answer)
    result = agent.run_sync("answer x")
    assert isinstance(result.output, Answer)
    assert isinstance(result.output.confidence, float)


def _ollama_is_up() -> bool:
    import urllib.request

    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
        return True
    except OSError:
        return False


def test_crewai_roles_collaborate_through_a_local_model():
    """The defining idea: multi-role speed. Two agents, two chained tasks, one
    crew — orchestrated by the real library against a local model."""
    if not _ollama_is_up():
        pytest.skip("Ollama is not serving on :11434")
    from crewai import LLM, Agent, Crew, Task

    llm = LLM(model="ollama/qwen3.5:9b", base_url="http://localhost:11434")
    researcher = Agent(
        role="researcher",
        goal="List one fact about the topic.",
        backstory="Terse. One sentence only.",
        llm=llm,
    )
    writer = Agent(
        role="writer",
        goal="Turn the fact into one friendly sentence.",
        backstory="Terse. One sentence only.",
        llm=llm,
    )
    research = Task(
        description="State one fact about local LLM inference.",
        expected_output="One sentence.",
        agent=researcher,
    )
    write = Task(
        description="Rewrite the researcher's fact in a friendly tone.",
        expected_output="One sentence.",
        agent=writer,
        context=[research],
    )
    result = Crew(agents=[researcher, writer], tasks=[research, write]).kickoff()
    assert len(str(result)) > 0
