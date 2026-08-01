"""Four kinds of memory behind one interface — your job.

"Give it memory" is four features, not one. A chat turn, a past incident, a durable
fact about the user, and a hard-won procedure have four different lifetimes and four
different failure modes. Keep them in ONE Qdrant collection separated by payload:
`(user, kind)` is the namespace. Get that right and you get, almost for free:

    recall            -> a filtered vector search, per user and per kind
    forget(id)        -> a point deleted, not merely outranked
    forget_all(kind)  -> "forget everything you know about me" as one filter delete
    expiry            -> a stale fact stops being recallable without a cron job

What is already here: the `Memory` record, both embedders, the collection setup, the
report. What you implement: the write path, the recall path, both forget paths, and
the filter that makes namespaces and expiry work.

Run `make test` first. Read the failures — they are the spec.
"""

from __future__ import annotations

import hashlib
import math
import re
import time
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
        """Store one claim and return its id.

        TODO: refuse an empty `text`, and refuse a blank `source` — a memory with no
              provenance cannot be audited later, so it does not get to exist.
        TODO: `models.PointStruct(id=..., vector=self.embed(text), ...)` — the id has to
              be a UUID string (`uuid.uuid4()`; import it), because Qdrant only accepts
              unsigned ints or UUIDs as point ids.
              with a payload carrying user, kind, text, source, written_at, expires_at.
        TODO: `ttl_days=None` means "until superseded"; otherwise the expiry is
              `written_at + ttl_days * DAY_SECONDS`. Store `None`, not 0 — the
              difference is what the recall filter has to reason about.
        """
        raise NotImplementedError("write() is yours to implement")

    # ------------------------------------------------------------ recall path
    def recall(self, kind: Kind, query: str, k: int = 5, now: float | None = None) -> list[Memory]:
        """Top-k within one namespace, with expired rows excluded by the store.

        TODO: `self.client.query_points(...)` with `query=self.embed(query)`,
              `query_filter=self._filter(kind, now)`, `limit=k`, `with_payload=True`.
        TODO: map the hits through `_to_memory` and keep the score.
        """
        raise NotImplementedError("recall() is yours to implement")

    def all(self, kind: Kind | None = None) -> list[Memory]:
        """Everything stored (including expired rows) — for reports and debugging.

        TODO: `self.client.scroll(...)` with `scroll_filter=models.Filter(must=self._scope(kind))`.
              Scroll, not search: listing is not ranking, and there is no query here.
        TODO: return them sorted by `written_at` so a report reads chronologically.
        """
        raise NotImplementedError("all() is yours to implement")

    # ----------------------------------------------------------- forget paths
    def forget(self, memory_id: str) -> None:
        """Delete one row. A corrected fact must be *gone*, not ranked second.

        TODO: `points_selector=models.PointIdsList(points=[memory_id])`.
        """
        raise NotImplementedError("forget() is yours to implement")

    def forget_all(self, kind: Kind | None = None) -> int:
        """Drop a whole namespace and return how many rows went.

        TODO: `points_selector=models.FilterSelector(filter=models.Filter(must=...))`.
              Count the rows BEFORE you delete them, for obvious reasons.
        """
        raise NotImplementedError("forget_all() is yours to implement")

    # ------------------------------------------------------------------ inner
    def _scope(self, kind: Kind | None) -> list[models.Condition]:
        """The `(user, kind)` namespace as filter conditions — the whole isolation story.

        TODO: always match `user`; match `kind` too when one was given.
              Annotate the list as `list[models.Condition]`, not `list[FieldCondition]`,
              or the type checker will (correctly) object at the call site.
        """
        raise NotImplementedError("_scope() is yours to implement")

    def _filter(self, kind: Kind, now: float | None) -> models.Filter:
        """`(user, kind)` plus the TTL rule, evaluated by the store, not in Python.

        TODO: `must=self._scope(kind)`.
        TODO: the TTL clause needs `min_should` with `min_count=1`, because "not
              expired" is two cases: `models.IsNullCondition(...)` for rows with no
              expiry at all, and `models.Range(gte=cutoff)` for rows whose expiry is
              still in the future. A plain range condition drops every `null` row —
              a bug that looks like amnesia and takes an afternoon to find.
        """
        raise NotImplementedError("_filter() is yours to implement")


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
    """Route a claim to a kind.

    A deliberately dumb rule-based router, so the *decision* stays visible in the
    data instead of hiding inside a prompt. Real systems use a small model here.

    TODO: procedural = how to do a job ("retry ... on a 429", "always call X first").
    TODO: episodic = a specific past event ("failed when", "last Tuesday", a date).
    TODO: semantic = a durable fact about the user ("prefers", "works in", "is my").
    TODO: anything else is working memory — this run, and no longer.
    """
    raise NotImplementedError("classify() is yours to implement")


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
