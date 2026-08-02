"""Persistent audit log — who did what, decided by which policy, backed by SQLite.

The agent's per-request `audit` list answers "what happened in THIS run"; this
log answers the operator's question a week later: which identity asked for the
send, when was it approved, what did the guardrails block. Every row carries the
verified subject, so with auth on the trail is attributable.

Kinds recorded by the service:
    policy.blocked      input refused by guardrails (detail = reason)
    tool.pending        a gated tool paused for approval
    tool.ran            any tool executed inside the agent loop
    approval.granted    /approve minted one single-use grant
    approval.replayed   /approve replayed (idempotency key already seen)

Rows for a gated tool carry the id of the grant its execution spent, so the
approval, the span attribute and the trail all name the same record.

Shares the ASSISTANT_DB file when configured, so the trail survives a restart
alongside memory, approvals and the idempotency table.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class AuditEntry:
    at: str
    kind: str
    subject: str
    detail: str


class AuditLog:
    def __init__(self, path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS audit_log ("
            "  seq INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  at TEXT NOT NULL DEFAULT (datetime('now')),"
            "  kind TEXT NOT NULL,"
            "  subject TEXT NOT NULL,"
            "  detail TEXT NOT NULL"
            ")"
        )
        self._conn.commit()

    def record(self, kind: str, subject: str, detail: str) -> None:
        self._conn.execute(
            "INSERT INTO audit_log (kind, subject, detail) VALUES (?, ?, ?)",
            (kind, subject, detail),
        )
        self._conn.commit()

    def entries(self, kind: str | None = None) -> list[AuditEntry]:
        query = "SELECT at, kind, subject, detail FROM audit_log"
        params: tuple = ()
        if kind is not None:
            query += " WHERE kind = ?"
            params = (kind,)
        rows = self._conn.execute(query + " ORDER BY seq", params).fetchall()
        return [AuditEntry(*row) for row in rows]
