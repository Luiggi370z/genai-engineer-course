"""Two rented implementations of the same protocol: Mem0 2.x and LangMem 0.0.30.

Both satisfy `MemoryStore`, both run against local models with no API key, and both
have a rough edge the other does not — which is the entire point of running one
contract suite over both:

  Mem0     a memory *service*. `add()` runs an LLM on the write path by default to
           extract and consolidate facts; `infer=False` turns that off and stores what
           you gave it. Expiry is native (`expiration_date`), and `search` takes
           `filters={"user_id": ...}` — the bare `user_id=` kwarg is the 1.x form.

  LangMem  typed memory schemas over LangGraph's store. The store is the durable part;
           LangMem adds extraction and a pair of agent tools. There is no TTL concept,
           so the adapter enforces expiry itself — a real asymmetry, made harmless by
           the fact that the contract, not the vendor, defines what "expired" means.

Neither adapter needs a hosted key. Mem0 needs Ollama (embedder); LangMem needs
nothing at all, because writing and searching a store does not require a model.

Rule for this lesson: **run before you write.** Both libraries have moved recently, so
open a REPL, call the method, print what comes back, and only then write the adapter.
The docstrings below tell you which calls to make; they do not save you from checking.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

from src.store import DAY_SECONDS, FakeStore, Kind, Memory, MemoryStore, words

KINDS: tuple[Kind, ...] = ("working", "episodic", "semantic", "procedural")

# ------------------------------------------------------------------------- mem0
#: Local-only Mem0 config: Ollama for embeddings and the LLM, Qdrant in memory.
MEM0_CONFIG: dict[str, Any] = {
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "mem0_lesson",
            "embedding_model_dims": 768,  # nomic-embed-text
            "on_disk": False,
        },
    },
    "embedder": {"provider": "ollama", "config": {"model": "nomic-embed-text"}},
    "llm": {"provider": "ollama", "config": {"model": "qwen3-coder:30b"}},
}


class Mem0Store:
    """Mem0 behind our protocol. Namespace goes in `user_id`, provenance in metadata."""

    def __init__(self, user: str = "me", config: dict[str, Any] | None = None) -> None:
        from mem0 import Memory as Mem0Memory

        self.user = user
        self.client = Mem0Memory.from_config(config or MEM0_CONFIG)

    def _namespace(self, kind: Kind) -> str:
        return f"{self.user}:{kind}"

    def write(
        self,
        kind: Kind,
        text: str,
        *,
        source: str,
        ttl_days: int | None = None,
        now: float | None = None,
    ) -> str:
        """TODO: `self.client.add(text, user_id=..., metadata=..., infer=..., expiration_date=...)`

        Three decisions hide in that one call:
          * the namespace goes in `user_id` (`self._namespace(kind)`), so kinds stay apart
          * `metadata` is where provenance lives — Mem0 will not invent it for you
          * `infer=True` (the default!) sends your text to an LLM to be rewritten and
            merged with existing memories. That is Mem0's selling point AND an
            unbudgeted call on the write path. Pick deliberately and say why.
        Mem0 wants a DATE string for `expiration_date` — see `_as_date`, and get the
        timestamp from `expiry(ttl_days, now)` in `store.py` (you add the import).
        Return the id from `result["results"][0]["id"]`.
        """
        raise NotImplementedError("Mem0Store.write is yours to implement")

    def recall(self, kind: Kind, query: str, k: int = 5, now: float | None = None) -> list[Memory]:
        """TODO: `self.client.search(query, filters={"user_id": ...}, top_k=k)`.

        Two traps: it is `filters=`, not the `user_id=` kwarg you will find in older
        tutorials (that is the 1.x API), and it is `top_k`, not `limit`. Map each row
        in `["results"]` onto our `Memory`, pulling the source back out of `metadata`.
        Mem0 evaluates expiry against the real clock, so `now` steers writes only.
        """
        raise NotImplementedError("Mem0Store.recall is yours to implement")

    def forget(self, memory_id: str) -> None:
        self.client.delete(memory_id)

    def count(self, kind: Kind | None = None) -> int:
        kinds: list[Kind] = [kind] if kind else list(KINDS)
        total = 0
        for one in kinds:
            rows = self.client.get_all(filters={"user_id": self._namespace(one)}, show_expired=True)
            total += len(rows["results"])
        return total


def _as_date(timestamp: float) -> str:
    """Mem0 takes a date string for `expiration_date`, not a timestamp."""
    return datetime.fromtimestamp(timestamp, tz=UTC).date().isoformat()


# ---------------------------------------------------------------------- langmem
class LangMemStore:
    """LangMem's typed schema + manage tool over a LangGraph store.

    Two things become visible as soon as you write the adapter. First, LangMem's write
    path is a *tool* meant to be called by an agent — handing it a typed schema is what
    lets provenance ride along. Second, reads come straight from the LangGraph store,
    because that is where the data actually lives; the framework is the layer on top.
    """

    def __init__(self, user: str = "me", dim: int = 96) -> None:
        from langgraph.store.base import IndexConfig
        from langgraph.store.memory import InMemoryStore

        self.user = user
        self.dim = dim
        index: IndexConfig = {"dims": dim, "embed": self._embed}
        self.store = InMemoryStore(index=index)
        self._tools: dict[str, Any] = {}

    def _embed(self, texts: Sequence[str]) -> list[list[float]]:
        """A deterministic embedder so the contract suite stays offline and repeatable.

        Point this at `OllamaEmbeddings` or any LangChain embeddings object in
        production — the adapter does not otherwise change.
        """
        out: list[list[float]] = []
        for text in texts:
            vec = [0.0] * self.dim
            for word in words(text):
                vec[_hash_word(word) % self.dim] += 1.0
            norm = sum(value * value for value in vec) ** 0.5
            out.append([value / norm for value in vec] if norm else vec)
        return out

    def _namespace(self, kind: Kind) -> tuple[str, ...]:
        return ("memories", self.user, kind)

    def _manage(self, kind: Kind) -> Any:
        from langmem import create_manage_memory_tool

        if kind not in self._tools:
            self._tools[kind] = create_manage_memory_tool(
                namespace=self._namespace(kind), store=self.store, schema=fact_schema()
            )
        return self._tools[kind]

    def write(
        self,
        kind: Kind,
        text: str,
        *,
        source: str,
        ttl_days: int | None = None,
        now: float | None = None,
    ) -> str:
        """TODO: build a `fact_schema()` instance and hand it to the manage tool:
        `self._manage(kind).invoke({"content": fact.model_dump(), "action": "create"})`.

        Compute the expiry with `expiry(ttl_days, now)` from `store.py`.
        The tool returns a human sentence ("created memory <uuid>"), not an object — so
        the id has to be parsed out of it. Yes, really. Print it once and see.
        """
        raise NotImplementedError("LangMemStore.write is yours to implement")

    def recall(self, kind: Kind, query: str, k: int = 5, now: float | None = None) -> list[Memory]:
        """TODO: read from the LangGraph store: `self.store.search(ns, query=..., limit=...)`.

        Then two things the framework will not do for you:
          * unwrap the stored value with `_unwrap` — print `item.value` once and you
            will see why that helper exists
          * enforce the TTL yourself. LangMem and the LangGraph store have no expiry
            concept, so "expired" means whatever YOUR contract says it means. This is
            what owning the interface buys you.
        Fetch more candidates than `k`, score with `overlap` (from `store.py`), cut to `k`.
        """
        raise NotImplementedError("LangMemStore.recall is yours to implement")

    def forget(self, memory_id: str) -> None:
        for kind in KINDS:
            self.store.delete(self._namespace(kind), memory_id)

    def count(self, kind: Kind | None = None) -> int:
        kinds: list[Kind] = [kind] if kind else list(KINDS)
        return sum(len(self.store.search(self._namespace(one), limit=1000)) for one in kinds)


def _unwrap(value: dict[str, Any]) -> dict[str, Any]:
    """LangMem nests the typed schema under `content`, so stored rows look like
    `{"content": {"content": ..., "source": ..., "expires_at": ...}}`.

    Nobody documents that; you find it by reading what came back out. Absorbing shapes
    like this one is exactly the job of an adapter — and the reason the rest of your
    codebase should never import a vendor's types.
    """
    inner = value.get("content")
    if isinstance(inner, dict):
        return inner
    return {"content": inner or "", "source": value.get("source", ""), "expires_at": None}


def _hash_word(word: str) -> int:
    from hashlib import blake2b

    return int.from_bytes(blake2b(word.encode(), digest_size=8).digest(), "big")


@lru_cache(maxsize=1)
def fact_schema() -> type:
    """LangMem's typed memory schema, defined lazily.

    Pydantic arrives with the frameworks, so the offline fast tier — which only ever
    builds `FakeStore` — must be able to import this module without it.
    """
    from pydantic import BaseModel, Field

    class Fact(BaseModel):
        """What LangMem stores. Provenance and expiry ride along inside the schema."""

        content: str
        source: str = Field(description="turn id, tool call or document this came from")
        expires_at: float | None = None

    return Fact


# ------------------------------------------------------------------- the factory
def build_store(name: str, user: str = "me") -> MemoryStore:
    """One switch, so the contract suite can parametrise over every adapter you ship."""
    if name == "fake":
        return FakeStore(user)
    if name == "mem0":
        return Mem0Store(user)
    if name == "langmem":
        return LangMemStore(user)
    raise ValueError(f"unknown store {name!r}")


__all__ = ["DAY_SECONDS", "KINDS", "MEM0_CONFIG", "LangMemStore", "Mem0Store", "build_store"]
