"""Four kinds of memory behind one interface, on the retrieval stack you already know.

"Give it memory" is four features, not one. A chat turn, a past incident, a durable
fact about the user, and a hard-won procedure have four different lifetimes and four
different failure modes. This module keeps them in ONE Qdrant collection separated by
payload — `(user, kind)` is the namespace — because that is how you get:

    recall            -> a filtered vector search, per user and per kind
    forget(id)        -> a point deleted, not merely outranked
    forget_all(kind)  -> "forget everything you know about me" as one filter delete
    expiry            -> a stale fact stops being recallable without a cron job

Qdrant runs IN-MEMORY here (`QdrantClient(":memory:")`) — identical API to a real
server. The embedder is injected: a deterministic hash embedder keeps the fast tier
offline, and `fastembed_embedder()` is the real thing in the integration tier.
"""

from __future__ import annotations

import hashlib
import math
import re
import time
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Literal

from qdrant_client import QdrantClient, models

Kind = Literal["working", "episodic", "semantic", "procedural"]
KINDS: tuple[Kind, ...] = ("working", "episodic", "semantic", "procedural")

#: An embedder is any text -> vector callable. Injecting it is what keeps the fast
#: tier offline and lets production swap in a hosted model without touching this file.
Embedder = Callable[[str], list[float]]

DAY_SECONDS = 86_400


@dataclass(frozen=True)
class Memory:
    """A remembered claim, with the paperwork that makes it auditable.

    `source` is the non-negotiable field: without it, a wrong answer is untraceable
    and the one bad row that caused it is undeletable.
    """

    id: str
    kind: Kind
    text: str
    source: str
    written_at: float
    expires_at: float | None = None
    score: float = 0.0

    def is_expired(self, now: float | None = None) -> bool:
        moment = time.time() if now is None else now
        return self.expires_at is not None and self.expires_at < moment


# --------------------------------------------------------------------- embedders
def hash_embedder(dim: int = 96) -> Embedder:
    """A deterministic bag-of-words embedder: no model, no network, same vector always.

    It captures word overlap and nothing else — which is exactly enough to test
    namespacing, expiry and deletion. Semantic paraphrase recall is a different
    claim, so it gets tested against real embeddings in the integration tier.
    """
    token = re.compile(r"[a-z0-9]+")

    def embed(text: str) -> list[float]:
        vec = [0.0] * dim
        for word in token.findall(text.lower()):
            digest = hashlib.blake2b(word.encode(), digest_size=8).digest()
            vec[int.from_bytes(digest, "big") % dim] += 1.0
        norm = math.sqrt(sum(v * v for v in vec))
        return [v / norm for v in vec] if norm else vec

    return embed


def fastembed_embedder(model: str = "BAAI/bge-small-en-v1.5") -> Embedder:
    """Real local embeddings (ONNX, no API key). Downloads weights on first use."""
    from fastembed import TextEmbedding

    encoder = TextEmbedding(model_name=model)

    def embed(text: str) -> list[float]:
        return next(iter(encoder.embed([text]))).tolist()

    return embed


# ------------------------------------------------------------------- the store
class VectorMemory:
    """One collection, namespaced by `(user, kind)` in the payload.

    Separate collections per kind would also work, but payload namespacing is what
    scales to many users and gives you a filter-delete for "forget everything".
    """

    def __init__(
        self,
        embed: Embedder,
        *,
        user: str = "me",
        client: QdrantClient | None = None,
        collection: str = "memories",
    ) -> None:
        self.embed = embed
        self.user = user
        self.collection = collection
        self.client = client or QdrantClient(":memory:")
        size = len(embed("dimension probe"))
        if not self.client.collection_exists(collection):
            self.client.create_collection(
                collection,
                vectors_config=models.VectorParams(size=size, distance=models.Distance.COSINE),
            )

    # ------------------------------------------------------------- write path
    def write(
        self,
        kind: Kind,
        text: str,
        *,
        source: str,
        ttl_days: int | None = None,
        now: float | None = None,
    ) -> str:
        """Store one claim. `source` is required; `ttl_days=None` means "until superseded".

        Write less than you think: every remembered sentence is a permanent tax on
        recall precision. If it would not change a future answer, do not store it.
        """
        if not text.strip():
            raise ValueError("refusing to remember an empty string")
        if not source.strip():
            raise ValueError("every memory needs a source — provenance is not optional")
        written_at = time.time() if now is None else now
        expires_at = None if ttl_days is None else written_at + ttl_days * DAY_SECONDS
        memory_id = str(uuid.uuid4())
        self.client.upsert(
            self.collection,
            points=[
                models.PointStruct(
                    id=memory_id,
                    vector=self.embed(text),
                    payload={
                        "user": self.user,
                        "kind": kind,
                        "text": text,
                        "source": source,
                        "written_at": written_at,
                        "expires_at": expires_at,
                    },
                )
            ],
        )
        return memory_id

    # ------------------------------------------------------------ recall path
    def recall(self, kind: Kind, query: str, k: int = 5, now: float | None = None) -> list[Memory]:
        """Top-k within one namespace, expired rows excluded by the store itself."""
        hits = self.client.query_points(
            self.collection,
            query=self.embed(query),
            query_filter=self._filter(kind, now),
            limit=k,
            with_payload=True,
        ).points
        return [_to_memory(str(h.id), h.payload or {}, h.score or 0.0) for h in hits]

    def all(self, kind: Kind | None = None) -> list[Memory]:
        """Everything stored (including expired rows) — for reports and debugging."""
        scope = models.Filter(must=self._scope(kind))
        points, _ = self.client.scroll(
            self.collection, scroll_filter=scope, limit=10_000, with_payload=True
        )
        rows = [_to_memory(str(p.id), p.payload or {}) for p in points]
        return sorted(rows, key=lambda m: m.written_at)

    # ----------------------------------------------------------- forget paths
    def forget(self, memory_id: str) -> None:
        """Delete one row. A corrected fact must be *gone*, not ranked second."""
        self.client.delete(self.collection, points_selector=models.PointIdsList(points=[memory_id]))

    def forget_all(self, kind: Kind | None = None) -> int:
        """Drop a whole namespace — the machinery behind "forget what I told you"."""
        doomed = self.all(kind)
        self.client.delete(
            self.collection,
            points_selector=models.FilterSelector(filter=models.Filter(must=self._scope(kind))),
        )
        return len(doomed)

    # ------------------------------------------------------------------ inner
    def _scope(self, kind: Kind | None) -> list[models.Condition]:
        """The `(user, kind)` namespace as filter conditions — the whole isolation story."""
        scope: list[models.Condition] = [
            models.FieldCondition(key="user", match=models.MatchValue(value=self.user))
        ]
        if kind is not None:
            scope.append(models.FieldCondition(key="kind", match=models.MatchValue(value=kind)))
        return scope

    def _filter(self, kind: Kind, now: float | None) -> models.Filter:
        """`(user, kind)` plus the TTL rule, evaluated by the store, not in Python.

        The TTL clause needs `min_should` because "not expired" is two cases: the
        row has no expiry at all, or its expiry is still in the future. A plain
        range condition silently drops every `null` row — a bug that looks like
        amnesia and takes an afternoon to find.
        """
        cutoff = time.time() if now is None else now
        return models.Filter(
            must=self._scope(kind),
            min_should=models.MinShould(
                conditions=[
                    models.IsNullCondition(is_null=models.PayloadField(key="expires_at")),
                    models.FieldCondition(key="expires_at", range=models.Range(gte=cutoff)),
                ],
                min_count=1,
            ),
        )


def _to_memory(point_id: str, payload: dict, score: float = 0.0) -> Memory:
    return Memory(
        id=point_id,
        kind=payload.get("kind", "semantic"),
        text=payload.get("text", ""),
        source=payload.get("source", ""),
        written_at=payload.get("written_at", 0.0),
        expires_at=payload.get("expires_at"),
        score=score,
    )


# ------------------------------------------------------------------ the report
def classify(text: str) -> Kind:
    """A deliberately dumb router, so the *decision* stays visible in the data.

    Real systems use a small model here. Keeping it as rules in one function means
    a misfiled memory is a test case you can read, not a prompt you have to argue
    with — and it is a reminder that this decision is yours to make explicitly.
    """
    lowered = text.lower()
    if re.search(r"\b(retry|use the|always call|prefer|workaround|step \d)\b", lowered):
        return "procedural"
    episodic = r"\b(yesterday|last (week|month|tuesday)|on \d{4}-\d{2}-\d{2}|failed when)\b"
    if re.search(episodic, lowered):
        return "episodic"
    if re.search(r"\b(prefers?|works in|lives in|is my|timezone|manager|team)\b", lowered):
        return "semantic"
    return "working"


def report(store: VectorMemory, now: float | None = None) -> str:
    """What is in memory, per kind, and how much of it has gone stale."""
    lines = [f"user={store.user}"]
    for kind in KINDS:
        rows = store.all(kind)
        stale = sum(row.is_expired(now) for row in rows)
        no_source = sum(not row.source for row in rows)
        lines.append(
            f"  {kind:<11} {len(rows):>3} rows   expired={stale}   missing source={no_source}"
        )
    return "\n".join(lines)


def _demo_rows() -> Iterable[tuple[Kind, str, str, int | None]]:
    return [
        ("semantic", "Lu works in UTC-5 and prefers meetings after 10:00", "turn-3", None),
        ("semantic", "Dana is my manager for budget threads", "turn-4", 90),
        ("episodic", "The calendar tool failed when the event had no end time", "run-12", None),
        ("procedural", "Retry the calendar tool once on a 429, then ask the user", "run-12", None),
        ("working", "Draft the Q3 budget summary for review", "turn-9", None),
    ]


def main() -> None:
    store = VectorMemory(hash_embedder())
    for kind, text, source, ttl in _demo_rows():
        store.write(kind, text, source=source, ttl_days=ttl)
    print(report(store))
    print("\nrecall(semantic, 'what timezone does Lu work in?'):")
    for memory in store.recall("semantic", "what timezone does Lu work in?", k=2):
        print(f"  {memory.text}   [{memory.source}]")


if __name__ == "__main__":
    main()
