# 5.4 Mem0 vs LangMem

**Goal.** Implement one memory protocol three times — an offline `FakeStore`, Mem0,
LangMem — and run a single contract suite over all three, so "we could swap vendors"
is a claim you can prove rather than a hope.
**Prerequisite.** 5.1 Four kinds of memory (the protocol mirrors that store's API).
**Effort.** ~60 min · moderate.

## Do this

```bash
make setup && make test     # 10 failing tests — read them, they are the spec
$EDITOR src/store.py        # fill FakeStore: a dict, overlap() scoring, expiry
$EDITOR src/adapters.py     # then the two rented adapters (integration tier)
make check                  # green: ruff + pyright + pytest, all offline
```

## What the first failure means

`test_contract_holds_offline[a_written_fact_is_recallable]` fails because
`FakeStore.write` and `FakeStore.recall` aren't built yet. It's the first of seven
contract checks that every adapter must pass: store a claim, recall it by meaning
(here, `overlap()` word similarity), get the provenance back. Get the fake green
first — it is the control that tells you whether a later failure is your logic or
the vendor's.

## Done when

- [ ] `make check` is green (lint, types, fast tests).
- [ ] All seven contract checks pass against `FakeStore` — including the blank
      `source` refusal and the expired row that must not come back — without
      weakening the suite, which is the one move that defeats the exercise.
- [ ] `count()` sees expired rows that `recall()` hides: audits and recalls answer
      different questions.

## Stuck?

1. `FakeStore` is a dict keyed by `fingerprint(text)` — the helpers `overlap()`,
   `expiry()` and `words()` are already written. Filter expired rows inside
   `recall`, score the rest, sort, cut to `k`.
2. For the rentals, run before you write: both libraries moved recently. Mem0 2.x
   wants `search(query, filters={"user_id": ...}, top_k=k)` (the bare `user_id=`
   kwarg and `limit` are the 1.x forms), and LangMem's manage tool returns a
   sentence like "created memory <uuid>" and nests your schema under `content` —
   `_unwrap` exists because of that shape.

## Going further (optional integration lane)
`make test-integration` runs the same seven contract assertions against the real
Mem0 and LangMem libraries (14 tests). Needs Ollama running with `nomic-embed-text`
pulled for the Mem0 path — no hosted key, but both libraries pull heavy dependency
trees. Skippable in the sense that the fake proves your contract logic, but the
rented run is where this lesson's three API surprises actually live.
