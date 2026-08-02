# 2.2 Hybrid + rerank — reference

The real stack, wired together. **You write no algorithms here.**

| Job | Package used |
|---|---|
| keyword / sparse | `rank_bm25` (simple arm) · `fastembed` `Qdrant/bm25` (vector arm) |
| semantic / dense | `fastembed` `BAAI/bge-small-en-v1.5` (local ONNX) |
| store + fusion | `qdrant-client` — two `Prefetch` arms + `FusionQuery(Fusion.RRF)` |
| rerank | `fastembed` `TextCrossEncoder("BAAI/bge-reranker-base")` |

```bash
make check              # fast, offline: real Qdrant API with fixture vectors
make test-integration   # real embeddings + reranker (~90MB download, cached)
```

**Why in-memory Qdrant?** `QdrantClient(":memory:")` is the same client and the
same API as a deployed server — fusion included. Swap in `QdrantClient(url=...)`
and nothing else changes. That's why you learn the client, not the algorithm.

**What the tests prove:** `test_dense_only_misses_the_exact_id` shows a semantic
query can't retrieve `INV-88231`; `test_hybrid_finds_the_exact_id_via_the_sparse_arm`
shows the keyword arm rescues it — the entire reason hybrid exists.

## Concept → framework primitive

There's no hand-rolled fusion algorithm in this lesson to contrast — you wire
libraries, you don't write tf/idf or RRF math. The mapping that matters is
between the naive approach those libraries replace and what `HybridStore`
actually calls in Qdrant:

| the naive approach (no native hybrid support) | the primitive in Qdrant | what Qdrant adds |
|---|---|---|
| two separate indexes, one per arm, kept in sync by hand | one collection, two named vectors: `vectors_config={DENSE: ...}` + `sparse_vectors_config={SPARSE: ...}` | dense and sparse live on the same point, upserted in one `client.upsert()` call |
| hand-writing an RRF loop to merge two ranked lists | `client.query_points(prefetch=[Prefetch(dense_q, using=DENSE), Prefetch(sparse_q, using=SPARSE)], query=FusionQuery(fusion=Fusion.RRF))` | fusion runs server-side, in the same round trip — no client-side merge code |
| BM25 as a separate library call (`bm25_search()`, `rank_bm25.BM25Okapi`) | `fastembed.SparseTextEmbedding("Qdrant/bm25")` producing a `models.SparseVector` | BM25-as-a-vector: the same store, upsert, and fusion path handles keyword and semantic |
| comparing "before" and "after" fusion by hand | `HybridStore.dense_only()` next to `HybridStore.hybrid_search()` — same client, one extra prefetch arm | swapping single-arm for hybrid is a query change, not a new system |
| manually re-scoring the top candidates by eye | `fastembed.rerank.cross_encoder.TextCrossEncoder(...).rerank(query, passages)` | a cross-encoder trained for relevance, not a heuristic you invented |

**Two artifacts.** You now own two things that prove different skills: `make check`
proves the wiring is correct — the collection shape, the `Prefetch` arms, the
`FusionQuery`, the rerank call — against the real Qdrant API with fixture
vectors, and `make test-integration` proves the full pipeline actually works
end to end with real local embeddings and a real cross-encoder. The interview
skill is explaining why `dense_only` misses `INV-88231` and `hybrid_search`
doesn't — this table is where that explanation lives.
