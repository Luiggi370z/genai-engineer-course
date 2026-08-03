# 5.1 Four kinds of memory

**Goal.** Build a memory store the agent can audit, expire and delete: one Qdrant
collection, namespaced by `(user, kind)` in the payload, with a `forget` that
actually forgets — on the retrieval stack you already built in Phase 2.
**Prerequisite.** Phase 2 (you have written to and searched a Qdrant collection).
**Effort.** ~75 min to green on the fast tests · +20 min for the integration tier · ~2 h realistic first pass.

## Do this

```bash
make setup && make test     # 13 failing tests — read them, they are the spec
$EDITOR src/memory.py       # fill the write/recall/forget paths, the TTL filter, classify
make check                  # green: ruff + pyright + pytest, all offline
uv run python -m src.memory # the report you are working toward
```

## What the first failure means

`test_a_written_fact_is_recallable_with_its_source` fails because `write()` and
`recall()` aren't built yet. It's asking for the round trip: store one claim as a
Qdrant point whose payload carries user, kind, text, source and expiry, then get it
back from a filtered vector search with the source intact. Provenance is the
non-negotiable part — a memory you can't trace is a memory you can't delete later.

## Done when

- [ ] `make check` is green (lint, types, fast tests).
- [ ] Rows with no expiry survive the TTL filter — a plain range condition drops
      every `null` row, and `test_rows_without_an_expiry_survive_the_ttl_filter`
      exists purely to catch that.
- [ ] `forget` leaves an empty recall, not a lower rank (the test asserts `== []`,
      because a "deleted" fact that still ranks second will resurface in a prompt).

## Stuck?

1. Build `_scope` and `_filter` first — every read path goes through them, and once
   they exist `recall`, `all`, and `forget_all` are each about three lines. Use
   `scroll` for `all()`: listing is not ranking.
2. "Not expired" is two cases: no expiry at all, or expiry in the future. That is a
   `models.MinShould` with `min_count=1` over an `IsNullCondition` on `expires_at`
   and a `Range(gte=cutoff)` — not a single range condition.

## Going further (optional integration lane)
`make test-integration` runs the paraphrase-recall test against real fastembed
embeddings (`BAAI/bge-small-en-v1.5`). Needs no key or service — it downloads an
ONNX model on first run and executes locally. Skippable: the fast tier already
proves namespacing, expiry and deletion; only the "no shared words, same meaning"
claim needs real vectors.
