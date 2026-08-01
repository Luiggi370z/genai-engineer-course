# 8.4 Cost & latency — reference

The optimization ladder in order: exact cache → semantic cache → tier router, then a
budget gate that fails on the **tail** rather than the average.

Everything runs offline and deterministically: the clock is injected so TTL tests
don't sleep, and the embedder is injected so similarity is a number the test chose.
`make test-integration` swaps in a real `fastembed` model — the only way to find out
whether your threshold survives real English.

The two assertions worth reading before you start:

- `test_a_loose_threshold_answers_the_wrong_question` — the same semantic cache,
  at 0.95 and at 0.85, serving EU refund law to a US customer at one of them.
- `test_a_cache_hit_never_consults_the_router` — the rung order, pinned.
