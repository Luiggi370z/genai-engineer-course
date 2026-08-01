"""The interface you own. Frameworks are implementations you rent.

Memory frameworks are moving fast and consolidating faster. That is a bad reason to
avoid them and an excellent reason to keep them behind your own protocol: your agent
depends on `MemoryStore`, and Mem0 or LangMem is one adapter satisfying it. Swapping
vendors becomes a file, not a project — and the contract suite in `tests/` is the thing
you actually own.

`FakeStore` is the offline reference implementation, and the first one you write. It
exists so the contract suite can run on every commit with no model, no network and no
vendor — and so a failure in the fast tier means *your* logic broke rather than
someone's service being down.

Start here, then do the two rented adapters in `adapters.py`.
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
        """TODO: refuse a blank source, then store a `Memory` keyed by `fingerprint(...)`.
        Use `expiry(ttl_days, now)` so "no TTL" stays `None` rather than becoming 0.
        """
        raise NotImplementedError("FakeStore.write is yours to implement")

    def recall(self, kind: Kind, query: str, k: int = 5, now: float | None = None) -> list[Memory]:
        """TODO: rows of this kind that have not expired, scored with `overlap`, top k."""
        raise NotImplementedError("FakeStore.recall is yours to implement")

    def forget(self, memory_id: str) -> None:
        """TODO: delete the row. Forgetting an unknown id is a no-op, not an error."""
        raise NotImplementedError("FakeStore.forget is yours to implement")

    def count(self, kind: Kind | None = None) -> int:
        """TODO: how many rows, expired included, optionally within one kind."""
        raise NotImplementedError("FakeStore.count is yours to implement")
