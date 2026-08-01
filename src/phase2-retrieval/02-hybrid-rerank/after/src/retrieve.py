"""Hybrid retrieval the way real applications do it: libraries, not algorithms.

You do NOT implement BM25, cosine similarity, or RRF here. Every one of those is a
solved problem with a well-maintained package. Your job as an engineer is to know
WHICH tool does WHICH job, and wire them together correctly:

    keyword (sparse)  ->  rank_bm25  (or fastembed's Qdrant/bm25)
    semantic (dense)  ->  fastembed  (BAAI/bge-small-en-v1.5, local ONNX)
    store + fusion    ->  qdrant-client  (native hybrid, server-side RRF)
    rerank            ->  fastembed TextCrossEncoder (BAAI/bge-reranker-base)

Qdrant runs IN-MEMORY here (`QdrantClient(":memory:")`) — same API as the real
server, no Docker needed. Point it at a URL in production and nothing else changes.
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


# ---------------------------------------------------------------- the embedders
def dense_embedder(model: str = "BAAI/bge-small-en-v1.5"):
    """Real local dense embeddings via fastembed (ONNX, no API key)."""
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=model)


def sparse_embedder(model: str = "Qdrant/bm25"):
    """Real sparse (keyword) embeddings — BM25 as vectors, so Qdrant can fuse them."""
    from fastembed import SparseTextEmbedding

    return SparseTextEmbedding(model_name=model)


# ------------------------------------------------------------------- the store
class HybridStore:
    """A Qdrant collection holding BOTH a dense and a sparse vector per document.

    One `query_points` call retrieves from both arms and fuses them server-side
    with RRF. That's the entire hybrid search — no fusion code of your own.
    """

    def __init__(self, client: QdrantClient | None = None, name: str = "docs",
                 dense_size: int = 384) -> None:
        self.client = client or QdrantClient(":memory:")
        self.name = name
        if not self.client.collection_exists(name):
            self.client.create_collection(
                name,
                vectors_config={DENSE: models.VectorParams(
                    size=dense_size, distance=models.Distance.COSINE)},
                sparse_vectors_config={SPARSE: models.SparseVectorParams()},
            )

    def upsert(self, texts: list[str], dense_vecs: list[list[float]],
               sparse_vecs: list[models.SparseVector]) -> None:
        self.client.upsert(self.name, points=[
            models.PointStruct(
                id=i,
                vector={DENSE: d, SPARSE: s},
                payload={"text": t},
            )
            for i, (t, d, s) in enumerate(zip(texts, dense_vecs, sparse_vecs, strict=True))
        ])

    def hybrid_search(self, dense_q: list[float], sparse_q: models.SparseVector,
                      k: int = 5, candidates: int = 20) -> list[Hit]:
        """Dense + sparse in ONE query, fused by Qdrant with RRF. No math from you."""
        res = self.client.query_points(
            self.name,
            prefetch=[
                models.Prefetch(query=dense_q, using=DENSE, limit=candidates),
                models.Prefetch(query=sparse_q, using=SPARSE, limit=candidates),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),  # <- the fusion step
            limit=k,
            with_payload=True,
        )
        return [Hit((p.payload or {}).get("text", ""), p.score or 0.0) for p in res.points]

    def dense_only(self, dense_q: list[float], k: int = 5) -> list[Hit]:
        """Single-arm search, so you can MEASURE what hybrid adds."""
        res = self.client.query_points(self.name, query=dense_q, using=DENSE,
                                       limit=k, with_payload=True)
        return [Hit((p.payload or {}).get("text", ""), p.score or 0.0) for p in res.points]


# ------------------------------------------------------------- the simple arm
def bm25_search(corpus: list[str], query: str, k: int = 5) -> list[str]:
    """The 3-line keyword baseline with rank_bm25 — no tf/idf math written by you."""
    from rank_bm25 import BM25Okapi

    bm25 = BM25Okapi([d.lower().split() for d in corpus])
    return bm25.get_top_n(query.lower().split(), corpus, n=k)


# ---------------------------------------------------------------- the reranker
def rerank(query: str, passages: list[str], top_k: int = 5,
           model: str = "BAAI/bge-reranker-base") -> list[str]:
    """Cross-encoder rerank with fastembed. Retrieval is recall; THIS is precision."""
    from fastembed.rerank.cross_encoder import TextCrossEncoder

    encoder = TextCrossEncoder(model_name=model)
    scores = list(encoder.rerank(query, passages))
    ranked = sorted(zip(passages, scores, strict=True), key=lambda x: x[1], reverse=True)
    return [p for p, _ in ranked[:top_k]]


# ------------------------------------------------------- end-to-end convenience
def build_and_search(corpus: list[str], query: str, k: int = 3) -> list[str]:
    """The full real pipeline: embed -> index -> hybrid retrieve -> rerank."""
    dense_model, sparse_model = dense_embedder(), sparse_embedder()
    dense_vecs = [v.tolist() for v in dense_model.embed(corpus)]
    sparse_vecs = [
        models.SparseVector(indices=s.indices.tolist(), values=s.values.tolist())
        for s in sparse_model.embed(corpus)
    ]
    store = HybridStore(dense_size=len(dense_vecs[0]))
    store.upsert(corpus, dense_vecs, sparse_vecs)

    dq = next(iter(dense_model.query_embed(query))).tolist()
    sq_raw = next(iter(sparse_model.query_embed(query)))
    sq = models.SparseVector(indices=sq_raw.indices.tolist(), values=sq_raw.values.tolist())

    candidates = [h.text for h in store.hybrid_search(dq, sq, k=10)]
    return rerank(query, candidates, top_k=k)
