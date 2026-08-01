"""Tier 2: the same durable pause, in REAL LangGraph — interrupt() + a
checkpointer, resumed by thread_id, surviving a simulated process restart.

    make test-integration

Runs offline: the graph's nodes are deterministic functions, no model involved.
"""
from __future__ import annotations

import sqlite3
from typing import TypedDict

import pytest

pytestmark = pytest.mark.integration


class State(TypedDict, total=False):
    topic: str
    email: str
    approved: bool


def _build(checkpointer, sent: list[str]):
    """draft -> approve (interrupt! a human decides later) -> send."""
    from langgraph.graph import END, StateGraph
    from langgraph.types import interrupt

    def draft(state: State) -> dict:
        return {"email": f"re: {state.get('topic', '')}"}

    def approve(state: State) -> dict:
        # Suspends the run and persists state via the checkpointer. The bool
        # comes from whatever the human passes to Command(resume=...).
        ok = interrupt(f"Send this email? {state.get('email', '')}")
        return {"approved": bool(ok)}

    def send(state: State) -> dict:
        if state.get("approved"):
            sent.append(state.get("email", ""))
        return {}

    graph = StateGraph(State)
    graph.add_node("draft", draft)
    graph.add_node("approve", approve)
    graph.add_node("send", send)
    graph.set_entry_point("draft")
    graph.add_edge("draft", "approve")
    graph.add_edge("approve", "send")
    graph.add_edge("send", END)
    return graph.compile(checkpointer=checkpointer)


def test_interrupt_pauses_before_the_irreversible_step_and_resumes_by_thread_id():
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.types import Command

    sent: list[str] = []
    app = _build(MemorySaver(), sent)
    config = {"configurable": {"thread_id": "hitl-approve"}}

    result = app.invoke({"topic": "launch"}, config)
    assert "__interrupt__" in result  # the run is suspended, not finished
    assert sent == []  # containment: nothing fired while paused

    out = app.invoke(Command(resume=True), config)  # the human clicks approve
    assert out["approved"] is True
    assert sent == ["re: launch"]


def test_rejection_resumes_the_graph_without_firing_the_tool():
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.types import Command

    sent: list[str] = []
    app = _build(MemorySaver(), sent)
    config = {"configurable": {"thread_id": "hitl-reject"}}

    app.invoke({"topic": "launch"}, config)
    out = app.invoke(Command(resume=False), config)
    assert out["approved"] is False
    assert sent == []


def test_the_pause_survives_a_process_restart(tmp_path):
    """The whole reason HITL needs a real checkpointer: pause in one process,
    resume in another. Simulated here with two graph instances over one SQLite
    file — the second knows nothing the database doesn't."""
    from langgraph.checkpoint.sqlite import SqliteSaver
    from langgraph.types import Command

    db_path = tmp_path / "hitl.db"
    config = {"configurable": {"thread_id": "hitl-durable"}}

    sent_before: list[str] = []
    conn1 = sqlite3.connect(db_path, check_same_thread=False)
    app1 = _build(SqliteSaver(conn1), sent_before)
    app1.invoke({"topic": "quarterly report"}, config)
    assert sent_before == []
    conn1.close()  # the "crash"

    sent_after: list[str] = []
    conn2 = sqlite3.connect(db_path, check_same_thread=False)
    app2 = _build(SqliteSaver(conn2), sent_after)
    out = app2.invoke(Command(resume=True), config)
    assert out["approved"] is True
    assert sent_after == ["re: quarterly report"]
    conn2.close()
