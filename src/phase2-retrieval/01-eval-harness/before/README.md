# 2.1 Eval harness (build this one first)

The harness every later phase reuses. Fill the TODOs in `src/harness.py`
(tier 1, `rapidfuzz`, offline) and `src/ragas_eval.py` (tier 2, real RAGAS with a
pinned Ollama judge).

```bash
make setup && make test          # tier 1 gate
make test-integration            # tier 2, needs Ollama
```

Write a 30-question golden set over your own corpus: ~15 semantic, ~10
exact-match/jargon, ~5 unanswerable. Keep the `slice` field — slicing is how you
learn *where* retrieval is failing.
