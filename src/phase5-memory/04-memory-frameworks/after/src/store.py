"""The interface you own. Frameworks are implementations you rent.

Memory frameworks are moving fast and consolidating faster. That is a bad reason to
avoid them and an excellent reason to keep them behind your own protocol: your agent
depends on `MemoryStore`, and Mem0 or LangMem is one adapter satisfying it. Swapping
vendors becomes a file, not a project — and the contract suite in `tests/` is the thing
you actually own.

`FakeStore` is the offline reference implementation. It exists so the contract suite
can run on every commit with no model, no network and no vendor, and so a failure in
the fast tier means *your* logic broke rather than someone's service being down.
"""

from __future__ import annotations

import hashlib
import math
import re
import time
import uuid
from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

Kind = Literal["working", "episodic", "semantic", "procedural"]

DAY_SECONDS = 86_400
_WORD = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class Memory:
    """One remembered claim. `source` is what makes a wrong answer traceable."""

    id: str
    kind: Kind
    text: str
    source: str
    expires_at: float | None = None
    score: float = 0.0


@runtime_checkable
class MemoryStore(Protocol):
    """Four methods. Every adapter in this lesson implements exactly these.

    Deliberately small: the narrower the interface, the cheaper the swap. Anything a
    single vendor supports and the others do not stays *out* of here and lives in the
    adapter, or you have rented an interface instead of an implementation.
    """

    def write(
        self,
        kind: Kind,
        text: str,
        *,
        source: str,
        ttl_days: int | None = None,
        now: float | None = None,
    ) -> str:
        """Store a claim with its provenance; return an id you can `forget` later."""
        ...

    def recall(self, kind: Kind, query: str, k: int = 5, now: float | None = None) -> list[Memory]:
        """Top-k within one kind. Expired rows must not come back."""
        ...

    def forget(self, memory_id: str) -> None:
        """Delete one row. Not "rank it lower" — delete."""
        ...

    def count(self, kind: Kind | None = None) -> int:
        """How many rows are stored, expired ones included. For reports and tests."""
        ...


def words(text: str) -> list[str]:
    """Tokens, for the offline scorer and the offline embedder. No model involved."""
    return _WORD.findall(text.lower())


def overlap(query: str, text: str) -> float:
    """Word-overlap similarity: deterministic, offline, and honest about what it is."""
    left, right = set(words(query)), set(words(text))
    if not left or not right:
        return 0.0
    return len(left & right) / math.sqrt(len(left) * len(right))


def expiry(ttl_days: int | None, now: float | None) -> float | None:
    moment = time.time() if now is None else now
    return None if ttl_days is None else moment + ttl_days * DAY_SECONDS


def fingerprint(text: str) -> str:
    """Stable id for the same text, so a re-write is idempotent in the fake."""
    return str(uuid.UUID(hashlib.blake2b(text.encode(), digest_size=16).hexdigest()))


class FakeStore:
    """The offline reference implementation: a dict and a word-overlap score.

    It is not a toy — it is the control. When the contract suite fails against a real
    adapter but passes here, the bug is in the rental, not in your expectations.
    """

    def __init__(self, user: str = "me") -> None:
        self.user = user
        self._rows: dict[str, Memory] = {}

    def write(
        self,
        kind: Kind,
        text: str,
        *,
        source: str,
        ttl_days: int | None = None,
        now: float | None = None,
    ) -> str:
        if not source.strip():
            raise ValueError("every memory needs a source — provenance is not optional")
        memory_id = fingerprint(f"{self.user}:{kind}:{text}")
        self._rows[memory_id] = Memory(
            id=memory_id,
            kind=kind,
            text=text,
            source=source,
            expires_at=expiry(ttl_days, now),
        )
        return memory_id

    def recall(self, kind: Kind, query: str, k: int = 5, now: float | None = None) -> list[Memory]:
        moment = time.time() if now is None else now
        alive = [
            row
            for row in self._rows.values()
            if row.kind == kind and (row.expires_at is None or row.expires_at >= moment)
        ]
        scored = [
            Memory(row.id, row.kind, row.text, row.source, row.expires_at, overlap(query, row.text))
            for row in alive
        ]
        return sorted(scored, key=lambda row: -row.score)[:k]

    def forget(self, memory_id: str) -> None:
        self._rows.pop(memory_id, None)

    def count(self, kind: Kind | None = None) -> int:
        return sum(1 for row in self._rows.values() if kind is None or row.kind == kind)
