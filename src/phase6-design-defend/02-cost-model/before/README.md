# 6.2 Cost model

**Goal.** Build a $/query cost model for a 100K-queries/day workload and show how the levers compound in order: cache first (hits are ~free), then route the remaining misses to a local tier. This is the arithmetic you bring to a "why is our LLM bill so high?" conversation.
**Prerequisite.** none.
**Effort.** ~20 min · gentle

## Do this

```bash
make setup && make test     # 3 failing tests — read them, they are the spec
$EDITOR src/costmodel.py    # per_call_cost + daily_cost (cache -> route)
make check                  # green: ruff + pyright + pytest, all offline
```

## What the first failure means

`test_cache_reduces_cost` fails with `NotImplementedError`: there is no cost model at all yet. Start with `per_call_cost` — dollars for one call from the `PRICE` table (per-million-token input/output rates) — then build `daily_cost` on top of it, applying the cache before the routing split.

## Done when

- [ ] `make check` is green (lint, types, fast tests).
- [ ] `test_cache_then_route_roughly_halves_bill` passes: a 40% cache hit rate plus routing half the misses locally brings the daily bill to ≤55% of baseline.

## Stuck?

1. Order matters: the cache removes queries before routing ever sees them. Only the cache *misses* get split between the local and frontier tiers.
2. `PRICE` maps tier to `(input_rate, output_rate)` in dollars per million tokens, so one call costs `in_tokens * in_rate / 1e6 + out_tokens * out_rate / 1e6`. `daily_cost` = misses routed local at the `local` price (which is 0.0) plus the rest at `frontier`, times nothing extra — cache hits cost zero.

No integration lane: this is pure arithmetic over a static price table — nothing external to call.
