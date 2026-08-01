# 5.2 Context engineering

**Goal.** Spend the context window on purpose: four moves (keep, compress, evict,
park) and an `assemble()` that fills a prompt under a hard token cap without ever
truncating a claim or evicting a pin.
**Prerequisite.** 5.1 Four kinds of memory (these lines are what a recall returns).
**Effort.** ~60 min · moderate.

## Do this

```bash
make setup && make test      # 13 failing tests — read them, they are the spec
$EDITOR src/context.py       # fill dedupe, evict_superseded, compress, assemble
make check                   # green: ruff + pyright + pytest, all offline
uv run python -m src.context # the receipt you are working toward
```

## What the first failure means

`test_assembly_never_exceeds_the_budget` fails because `assemble()` isn't built yet.
It's asking for the core invariant: given a task, pinned lines and ranked candidates,
fill the window until the next line would not fit — and stop. The cap is arithmetic,
not a suggestion, and every other behaviour (parking, pinning, the `BudgetError`)
hangs off this loop.

## Done when

- [ ] `make check` is green (lint, types, fast tests).
- [ ] Pins survive budget pressure, and pins that alone exceed the budget raise
      `BudgetError` loudly (`test_pinning_more_than_the_budget_is_a_loud_error`).
- [ ] A line that does not fit is parked whole, never truncated — half a fact reads
      as a whole fact to the model, and the test checks the render for fragments.

## Stuck?

1. Do the three moves before the assembly: `dedupe`, `evict_superseded` and
   `compress` each have their own test, so you can get them green in isolation and
   then compose them inside `assemble()`.
2. `dedupe` compares with `fuzz.token_set_ratio(a, b, processor=default_process)`
   from `rapidfuzz` — the processor is not optional. In `assemble()`, the order is
   the design: task + pins first (mark them with `dataclasses.replace(line,
   pinned=True)`), then evict, dedupe, rank by score descending, and park whatever
   does not fit.

## Going further (optional integration lane)
`make test-integration` re-runs the budget check counted with the real `tiktoken`
`o200k_base` tokenizer instead of the word-count stand-in. Needs network once —
`get_encoding` downloads the BPE file on first use — but no key or GPU. Skippable:
the fast tier already proves the assembly logic; the real tokenizer only confirms
the budget holds in the units money is spent in.
