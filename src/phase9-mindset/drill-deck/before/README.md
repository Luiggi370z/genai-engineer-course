# 9.1 Drill deck

**Goal.** Turn the course question bank (`data/cards.jsonl`) into a weighted
spaced-repetition deck: fumbled cards resurface sooner, and repeat offenders land
on a leech list — your interview-prep priority queue.
**Prerequisite.** None — this is a standalone tool; the cards reference material
from every phase.
**Effort.** ~25 min to green on the fast tests · no integration tier · ~40 min realistic first pass.

## Do this

```bash
make setup && make test     # 3 failing tests — read them, they are the spec
$EDITOR src/deck.py         # TODOs 1-4: load, draw, grade, leech_list
make check                  # green: ruff + pyright + pytest, all offline
```

## What the first failure means

`test_load_and_draw` fails because `Deck.load` isn't built. It wants
`data/cards.jsonl` — one JSON object per line — parsed into `Card` objects, and
then `draw(3)` returning three *distinct* cards (the test asserts no repeats in
one draw). Drawing must weight each card by `misses + 1`, so a card you keep
getting wrong shows up more often than one you've never missed.

## Done when

- [ ] `make check` is green (lint, types, fast tests).
- [ ] `grade("qb-1", correct=False)` twice leaves that card with `misses == 2`.
- [ ] A card missed twice appears in `leech_list()`.

## Stuck?

1. `json.loads` per line handles the file. For the draw, note the injected
   `rng: random.Random` — the test seeds `Random(0)`, so use it for every random
   choice or the draw won't be reproducible.
2. Weighted sampling *without* replacement isn't what `rng.choices` gives you —
   pick one card at a time with weights `misses + 1` and remove it from the pool
   before the next pick.

No integration lane: the deck is stdlib plus a local JSONL file — there is nothing
external to call. The real exercise starts after green: draw five a day and answer
out loud before flipping.
