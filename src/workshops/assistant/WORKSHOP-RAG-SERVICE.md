# Workshop · Ship a real RAG service  (ends Phase 2)

**Effort.** ~2 h of focused build time · +60 min for the integration tier · ~4 h realistic first pass.

Build the assistant's retrieval core: hybrid search (keyword + vector, fused),
returning grounded chunks with an abstain path.

Three passes. **Minimum** is the walking skeleton — the smallest thing that is
really this, and a place to stop that is not quitting. **Full** is the version you
would show someone. **Stretch** is for when the full pass came easily.

## Minimum
- [ ] `RagStore.search(query, k)` returns relevant chunks
- [ ] Unanswerable questions get an abstention, not an invented answer

## Full
- [ ] Hybrid: exact IDs (e.g. INV-88231) are found, not just semantic matches
- [ ] Runs offline; the store sits behind an interface you could swap for Qdrant

## Stretch
- [ ] `docker compose up` with Qdrant + Ollama, zero API keys — the production shape
      Workshop 8 will require anyway
- [ ] Contextual chunks (`phase2-retrieval/04-contextual-chunks`) on the slice where
      recall is weakest, with the before/after number written down

Implement `rag.py`. Tests: `tests/test_rag.py`.
Next layer: `WORKSHOP-EVAL-SUITE.md` proves this one actually works.
