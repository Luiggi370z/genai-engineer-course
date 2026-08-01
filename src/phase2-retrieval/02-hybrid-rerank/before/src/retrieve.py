"""TODO: wire up hybrid search using real libraries. You will NOT write algorithms.

Nobody implements BM25 or cosine similarity at work — they pick the right package.
Your job is the wiring. Every TODO below is a few lines of library calls.

    keyword (sparse)  ->  rank_bm25.BM25Okapi   /  fastembed SparseTextEmbedding
    semantic (dense)  ->  fastembed TextEmbedding("BAAI/bge-small-en-v1.5")
    store + fusion    ->  qdrant_client: Prefetch x2 + FusionQuery(Fusion.RRF)
    rerank            ->  fastembed TextCrossEncoder("BAAI/bge-reranker-base")

Qdrant runs in-memory (`QdrantClient(":memory:")`) — the real API, no Docker.
Docs: https://qdrant.tech/documentation/concepts/hybrid-queries/
Reference: ../after/src/retrieve.py
"""
from __future__ import annotations

from dataclasses import dataclass

from qdrant_client import QdrantClient, models

DENSE = "dense"
SPARSE = "keywords"


@dataclass
class Hit:
    text: str
    score: float


def dense_embedder(model: str = "BAAI/bge-small-en-v1.5"):
    """TODO 1: return a fastembed TextEmbedding for real local dense vectors."""
    raise NotImplementedError


def sparse_embedder(model: str = "Qdrant/bm25"):
    """TODO 2: return a fastembed SparseTextEmbedding (BM25 as sparse vectors)."""
    raise NotImplementedError


class HybridStore:
    """A Qdrant collection with BOTH a dense and a sparse vector per document."""

    def __init__(self, client: QdrantClient | None = None, name: str = "docs",
                 dense_size: int = 384) -> None:
        self.client = client or QdrantClient(":memory:")
        self.name = name
        # TODO 3: create the collection with vectors_config={DENSE: VectorParams(...)}
        #         AND sparse_vectors_config={SPARSE: SparseVectorParams()}
        raise NotImplementedError

    def upsert(self, texts: list[str], dense_vecs: list[list[float]],
               sparse_vecs: list[models.SparseVector]) -> None:
        """TODO 4: upsert PointStructs carrying both vectors + a {"text": ...} payload."""
        raise NotImplementedError

    def hybrid_search(self, dense_q: list[float], sparse_q: models.SparseVector,
                      k: int = 5, candidates: int = 20) -> list[Hit]:
        """TODO 5: ONE query_points call with two Prefetch arms + FusionQuery(RRF).

        This is the whole lesson: you don't fuse rankings yourself, Qdrant does.
        """
        raise NotImplementedError

    def dense_only(self, dense_q: list[float], k: int = 5) -> list[Hit]:
        """TODO 6: single-arm dense search, so you can measure what hybrid adds."""
        raise NotImplementedError


def bm25_search(corpus: list[str], query: str, k: int = 5) -> list[str]:
    """TODO 7: three lines with rank_bm25.BM25Okapi + get_top_n. No tf/idf math."""
    raise NotImplementedError


def rerank(query: str, passages: list[str], top_k: int = 5,
           model: str = "BAAI/bge-reranker-base") -> list[str]:
    """TODO 8: score passages with fastembed TextCrossEncoder, return the best top_k."""
    raise NotImplementedError


def build_and_search(corpus: list[str], query: str, k: int = 3) -> list[str]:
    """TODO 9 (integration): embed -> index -> hybrid retrieve -> rerank."""
    raise NotImplementedError
