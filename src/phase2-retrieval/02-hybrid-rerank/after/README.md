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
