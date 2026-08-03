"""TODO: implement human-in-the-loop with a DURABLE pause. Twice.

Framework-free (`Runner`, TODO 1-2), then in real LangGraph (`approval_graph`,
TODO 3). Writing both is the point of the lesson: the second one looks obvious
until you place the interrupt and find out where it actually has to go.

- act(action, **args): if the action is irreversible (send/pay/delete/schedule),
  suspend: create a PendingApproval, PERSIST it, and return it. Otherwise run now.
- resume(token, approved): pop the pending approval; run it if approved, else reject.
- Persist pending approvals to disk so a pause survives a restart.
- approval_graph(checkpointer, send): the same three ideas as a LangGraph graph.

Reference: ../after/src/hitl.py.
"""
from __future__ import annotations

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
    def __init__(self, tools: dict[str, Callable[..., Any]], store: str | Path = ".hitl.json"):
        self.tools = tools
        self.store = Path(store)
        self._pending: dict[str, PendingApproval] = {}

    def act(self, action: str, **args: Any) -> Any:
        raise NotImplementedError  # TODO 1

    def resume(self, token: str, approved: bool) -> Any:
        raise NotImplementedError  # TODO 2


# --- the same pause, in real LangGraph ------------------------------------------


class State(TypedDict, total=False):
    topic: str
    email: str
    approved: bool


def approval_graph(checkpointer: Any, send: Callable[[str], None]) -> Any:
    """TODO 3: draft -> approve (interrupt!) -> send, compiled with `checkpointer`.

    Three nodes over `State`. `draft` writes an `email` from `topic`. `approve`
    calls `langgraph.types.interrupt(...)` and returns `{"approved": bool(...)}`
    from whatever comes back. `send` calls the injected `send(email)` — but only
    when `state["approved"]`. Wire draft -> approve -> send -> END, entry point
    `draft`, and return `graph.compile(checkpointer=checkpointer)`.

    Two things are easy to get subtly wrong, and the integration tests are
    written to catch both:

      * **Put the interrupt in its own node, before the effect.** Calling it
        partway through the node that sends pauses a run that has already sent.
      * **Make the effect depend on a value the paused node produces.** `send`
        reads `approved`, which does not exist until a human supplies it via
        `Command(resume=...)`. A gate that reads a flag somebody remembered to
        set is a gate that somebody eventually forgets.

    `checkpointer` is a parameter, not a choice this function makes: a
    `MemorySaver` pauses for the life of the process, a `SqliteSaver` outlives
    it, and the graph is identical either way. Durability is infrastructure.

    Import langgraph INSIDE the function — it is an integration-group dependency
    and this module has to import without it.
    """
    raise NotImplementedError  # TODO 3
