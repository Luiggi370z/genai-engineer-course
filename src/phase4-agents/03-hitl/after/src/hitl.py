"""Human-in-the-loop with a durable pause, written twice.

`Runner` is the concept, framework-free so it runs offline: an action classified
'irreversible' suspends the run and returns a PendingApproval, and a human calls
`resume(token, approved=...)` later — even after a restart, because pending
approvals are persisted.

`approval_graph` is the same three ideas in real LangGraph — `interrupt()`, a
checkpointer, resume by `thread_id`. It lives here rather than in the test file
because writing it is the lesson. A graph you only ever read is a graph you have
not learned; the pause looks obvious until you try to place the interrupt and
discover it has to sit BEFORE the effect, in its own node, with the effect
downstream of a value the node cannot compute.

Both are exercised by the same suite (`tests/test_hitl.py`,
`tests/test_integration.py`), so the comparison is concrete: the JSON runner
persists a pending record, the graph persists the whole run.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict

IRREVERSIBLE = {"send", "pay", "delete", "schedule"}


@dataclass
class PendingApproval:
    token: str
    action: str
    args: dict[str, Any]


class Runner:
    """Runs actions; pauses (durably) before irreversible ones."""

    def __init__(self, tools: dict[str, Callable[..., Any]], store: str | Path = ".hitl.json"):
        self.tools = tools
        self.store = Path(store)
        self._pending: dict[str, PendingApproval] = {}
        self._load()

    def _load(self) -> None:
        if self.store.exists():
            data = json.loads(self.store.read_text())
            self._pending = {
                k: PendingApproval(**v) for k, v in data.items()
            }

    def _save(self) -> None:
        self.store.write_text(
            json.dumps({k: vars(v) for k, v in self._pending.items()})
        )

    def act(self, action: str, **args: Any) -> Any:
        if action in IRREVERSIBLE:
            token = f"{action}-{len(self._pending)}"
            self._pending[token] = PendingApproval(token, action, args)
            self._save()  # persisted — survives a restart mid-pause
            return PendingApproval(token, action, args)
        return self.tools[action](**args)

    def resume(self, token: str, approved: bool) -> Any:
        p = self._pending.pop(token)
        self._save()
        if not approved:
            return {"status": "rejected", "action": p.action}
        return self.tools[p.action](**p.args)


# --- the same pause, in real LangGraph ------------------------------------------


class State(TypedDict, total=False):
    topic: str
    email: str
    approved: bool


def approval_graph(checkpointer: Any, send: Callable[[str], None]) -> Any:
    """draft -> approve (interrupt! a human decides later) -> send.

    Three decisions, each of which is the lesson:

    **The interrupt is its own node.** `interrupt()` suspends the run from
    inside `approve`, before `send` has been reached at all. Calling it partway
    through the node that sends would pause a run that had already sent.

    **The effect is downstream of a value the paused node produces.** `send`
    reads `approved`, which does not exist until a human supplies it through
    `Command(resume=...)`. The gate is a data dependency, not a flag somebody
    remembers to check.

    **The checkpointer is a parameter.** Handed a `MemorySaver`, the pause lasts
    as long as the process; handed a `SqliteSaver`, it outlives one. The graph
    does not change, which is the honest way to say that durability is an
    infrastructure choice and not a property of LangGraph.

    Imported lazily so the framework-free tier stays importable without it.
    """
    from langgraph.graph import END, StateGraph
    from langgraph.types import interrupt

    def draft(state: State) -> dict:
        return {"email": f"re: {state.get('topic', '')}"}

    def approve(state: State) -> dict:
        # Suspends the run and persists state via the checkpointer. The bool
        # comes from whatever the human passes to Command(resume=...).
        ok = interrupt(f"Send this email? {state.get('email', '')}")
        return {"approved": bool(ok)}

    def send_node(state: State) -> dict:
        if state.get("approved"):
            send(state.get("email", ""))
        return {}

    graph = StateGraph(State)
    graph.add_node("draft", draft)
    graph.add_node("approve", approve)
    graph.add_node("send", send_node)
    graph.set_entry_point("draft")
    graph.add_edge("draft", "approve")
    graph.add_edge("approve", "send")
    graph.add_edge("send", END)
    return graph.compile(checkpointer=checkpointer)
