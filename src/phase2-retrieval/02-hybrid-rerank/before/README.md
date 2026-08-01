# 2.2 Hybrid + rerank

**Goal.** Wire up production hybrid retrieval — a dense arm and a sparse arm
fused server-side by Qdrant, then a cross-encoder rerank on top. You implement
no algorithms; you pick and connect libraries, which is the actual job.
**Prerequisite.** 2.1 Eval harness (you saw that the exact-match slice is where
retrieval fails — this lesson is the fix).
**Effort.** ~50 min · moderate.

## Do this

```bash
make setup && make test     # 4 failing tests — read them, they are the spec
$EDITOR src/retrieve.py     # TODOs 1-9: embedders, hybrid store, BM25 baseline, rerank
make check                  # green: ruff + pyright + pytest, all offline
```

## What the first failure means

`test_dense_only_misses_the_exact_id` errors because `HybridStore.__init__`
isn't built. It wants a Qdrant collection carrying *both* a dense and a sparse
vector per document (`vectors_config` plus `sparse_vectors_config`). The test
then demonstrates why hybrid exists: a semantic query vector cannot match
`INV-88231`, and the sparse keyword arm is what rescues it.

## Done when

- [ ] `make check` is green (lint, types, fast tests).
- [ ] `test_hybrid_is_one_call_with_server_side_fusion` passes: `hybrid_search`
      is a single `query_points` call — Qdrant fuses the rankings, you don't.
- [ ] `test_bm25_library_finds_the_identifier` passes without you writing any
      tf/idf math.

## Stuck?

1. Every TODO is a few lines of library calls. The unit tests use
   `QdrantClient(":memory:")` — the exact same client and API as a deployed
   server, fusion included, so nothing you write here is test-only.
2. `hybrid_search` is two `models.Prefetch` arms (one per named vector) inside
   one `client.query_points(..., query=models.FusionQuery(fusion=models.Fusion.RRF))`.
   The Qdrant hybrid-queries docs page has the exact shape.

## Going further (optional integration lane)
`make test-integration` runs the same wiring with real local models — fastembed's
ONNX `bge-small-en-v1.5` embeddings and the `bge-reranker-base` cross-encoder,
end to end. Needs ~90MB of model weights on first run (cached after), no API
keys, no Docker. Skippable: the fast tier already proves the logic against the
real Qdrant API.
