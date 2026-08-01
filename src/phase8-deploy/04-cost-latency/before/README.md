# 8.4 Cost & latency

**Goal.** Climb the optimization ladder in risk order — exact cache, then semantic
cache, then tier router — and finish with a budget gate that fails on the P99 tail,
the cost per request, or the eval score, never reporting a saving without the
quality number next to it.
**Prerequisite.** 8.3 Deploy & observe — the percentile and spend-by-tier thinking
comes straight from there.
**Effort.** ~90 min · involved.

## Do this

```bash
make setup && make test     # 39 failing tests — read them, they are the spec
$EDITOR src/cache.py src/router.py src/ladder.py
make check                  # green: ruff + pyright + pytest, all offline
```

## What the first failure means

`test_the_key_covers_the_context_not_just_the_question` (in `test_cache.py`) fails
because `cache_key` isn't built. It pins the classic production bug: key on the
question alone, re-index the document behind it, and the cache confidently serves
last week's answer. The key must hash everything that changes the answer —
question (normalized), context, model, tier. From there the suite walks you up the
ladder: TTL'd exact cache, cosine + threshold semantic cache, sweep, router, and
finally `Ladder.ask` wiring the rungs in order.

## Done when

- [ ] `make check` is green (lint, types, fast tests).
- [ ] `test_a_loose_threshold_answers_the_wrong_question` passes: at 0.95 the
      semantic cache stays quiet, at 0.85 it serves EU refund law to a US customer.
- [ ] `test_a_cache_hit_never_consults_the_router` passes — the rung order, pinned.

## Stuck?

1. Work in dependency order: `cache.py` first (key, TTL get/put, `cosine`,
   `nearest`/`get`/`put`, `sweep`), then `router.py` (cost, classify, route), and
   only then wire `Ladder.ask`.
2. In `Ladder.ask`: exact cache → semantic cache (only if one was supplied) →
   route → backend. On a model answer, bill it with `tier.cost()`, write BOTH
   caches, and copy `downgraded_from` from the routing decision when the cost
   ceiling stepped it down.

## Going further (optional integration lane)
`make test-integration` runs the semantic cache and the threshold sweep against a
real fastembed embedding model (`BAAI/bge-small-en-v1.5`). Needs the `integration`
dependency group — the first run downloads a small ONNX model (tens of MB), CPU
only, free. Skippable: the fast tier already proves the cache logic with a
scripted embedder; this lane tells you whether your threshold survives real English.
