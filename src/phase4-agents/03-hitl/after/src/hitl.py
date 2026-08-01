"""Human-in-the-loop with a durable pause — the concept, framework-free so it runs
offline. (In the course you do this with LangGraph's interrupt() + a checkpointer;
the mechanics are identical: suspend, persist state, resume by id.)

An action classified 'irreversible' suspends the run and returns a PendingApproval.
A human calls resume(token, approved=True/False) later — even after a restart,
because pending approvals are persisted.
"""
from __future__ import annotations

import json
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
