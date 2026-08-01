"""The FIXED pipeline: ONE embedder for both indexing and querying.

The bug was a **mismatched embedding model** — documents indexed with model A,
queries embedded with model B. Same vector size, so nothing crashed; the vectors
simply lived in different spaces, making every similarity score meaningless.

The fix is structural, not a tweak: the embedder is now a single injected
dependency used by both paths, so the two can never drift apart again.
"""
from __future__ import annotations

from collections.abc import Callable

from qdrant_client import QdrantClient, models

Embedder = Callable[[str], list[float]]


def embedder_a(text: str) -> list[float]:
    """'Model A' — e.g. bge-small-en-v1.5. Direction encodes the topic."""
    t = text.lower()
    payments = float(any(w in t for w in ("invoice", "paid", "payment", "wire", "refund")))
    weather = float(any(w in t for w in ("weather", "sunny", "rain", "cloudy")))
    search = float(any(w in t for w in ("search", "retrieval", "keyword", "vector")))
    return [payments, weather, search]


def embedder_b(text: str) -> list[float]:
    """'Model B' — a DIFFERENT model. Same dimension, but the axes mean other things.

    Two models producing the same vector SIZE does not make their vectors
    comparable. This is the trap.
    """
    t = text.lower()
    search = float(any(w in t for w in ("search", "retrieval", "keyword", "vector")))
    payments = float(any(w in t for w in ("invoice", "paid", "payment", "wire", "refund")))
    weather = float(any(w in t for w in ("weather", "sunny", "rain", "cloudy")))
    return [search, weather, payments]  # axis order differs from model A!


class RAG:
    def __init__(self, docs: list[str], embed: Embedder | None = None) -> None:
        # ONE embedder, stored once, used for indexing AND querying.
        self.embed: Embedder = embed or embedder_a
        self.client = QdrantClient(":memory:")
        self.name = "docs"
        self.client.create_collection(
            self.name,
            vectors_config=models.VectorParams(size=3, distance=models.Distance.COSINE),
        )
        self.client.upsert(self.name, points=[
            models.PointStruct(id=i, vector=self.embed(d), payload={"text": d})
            for i, d in enumerate(docs)
        ])

    def retrieve(self, query: str, k: int = 2) -> list[str]:
        # FIX: the same embedder that built the index also embeds the query.
        qv = self.embed(query)
        res = self.client.query_points(self.name, query=qv, limit=k, with_payload=True)
        return [(p.payload or {}).get("text", "") for p in res.points]

    def answer(self, query: str) -> str:
        ctx = self.retrieve(query)
        if not ctx:
            return "I don't know"
        return f"Based on the docs: {ctx[0]}"
