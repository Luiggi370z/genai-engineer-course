# Workshop · Ship a real RAG service  (ends Phase 2)

Build the assistant's retrieval core: hybrid search (keyword + vector, fused),
returning grounded chunks with an abstain path.

## Deliverables
- [ ] `RagStore.search(query, k)` returns relevant chunks
- [ ] Hybrid: exact IDs (e.g. INV-88231) are found, not just semantic matches
- [ ] Runs offline; the store sits behind an interface you could swap for Qdrant
- [ ] (production) `docker compose up` with Qdrant + Ollama, zero API keys
- [ ] Unanswerable questions get an abstention, not an invented answer

Implement `rag.py`. Tests: `tests/test_rag.py`.
Next layer: `WORKSHOP-EVAL-SUITE.md` proves this one actually works.
