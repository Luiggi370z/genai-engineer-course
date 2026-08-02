"""Idempotency keys for the approval flow — a SQLite dedupe table.

An approval is a MUTATION: it grants one execution of an irreversible tool. A
client that retries a timed-out /approve (as every well-behaved client does)
must not grant a second run. The fix is the standard one: the client sends an
Idempotency-Key header, the server records it, and a key it has seen before is
acknowledged without re-applying the effect.

The table lives in the same SQLite file as memory when ASSISTANT_DB is set, so
replay protection survives a restart; without it, an in-process :memory: table
covers the single-process demo.
"""
from __future__ import annotations

import sqlite3


class IdempotencyStore:
    def __init__(self, path: str = ":memory:") -> None:
        # one long-lived connection: ':memory:' would otherwise vanish per call
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS idempotency_keys ("
            "  key TEXT PRIMARY KEY,"
            "  created_at TEXT NOT NULL DEFAULT (datetime('now'))"
            ")"
        )
        self._conn.commit()

    def seen(self, key: str) -> bool:
        """Record the key; report whether it was already there. INSERT OR IGNORE
        makes the check-and-set a single atomic statement."""
        cur = self._conn.execute(
            "INSERT OR IGNORE INTO idempotency_keys (key) VALUES (?)", (key,)
        )
        self._conn.commit()
        return cur.rowcount == 0
