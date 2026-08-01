"""TODO: implement human-in-the-loop with a DURABLE pause.

- act(action, **args): if the action is irreversible (send/pay/delete/schedule),
  suspend: create a PendingApproval, PERSIST it, and return it. Otherwise run now.
- resume(token, approved): pop the pending approval; run it if approved, else reject.
- Persist pending approvals to disk so a pause survives a restart.

In the course you'd use LangGraph interrupt() + a checkpointer; same mechanics.
Reference: ../after/src/hitl.py.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
