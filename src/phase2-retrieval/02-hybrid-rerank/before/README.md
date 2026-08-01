# 2.2 Hybrid + rerank

Wire up production hybrid retrieval. **No algorithm implementation** — you pick
and connect libraries, which is the actual job.

Nine small TODOs in `src/retrieve.py`:
`fastembed` for dense + sparse vectors, `qdrant-client` for the store and
server-side RRF fusion, `rank_bm25` for the simple keyword baseline, and
`fastembed`'s `TextCrossEncoder` to rerank.

```bash
make setup && make test          # offline unit tests (real Qdrant API)
make test-integration            # once you want real models
```

Docs you'll need: <https://qdrant.tech/documentation/concepts/hybrid-queries/>
The course's "The modern retrieval stack" card has the exact snippets.
