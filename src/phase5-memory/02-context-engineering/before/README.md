# 5.2 Context engineering

Spend the window on purpose: keep, compress, evict, park — under a hard cap.

```bash
make setup && make test        # 13 failures; the failures are the spec
uv run python -m src.context   # the receipt you're working toward
```

## Your job

In `src/context.py`, implement the four moves and the assembly that uses them:

| Function | The interesting part |
|---|---|
| `dedupe` | near-duplicates, not exact ones — `rapidfuzz` with `default_process` |
| `evict_superseded` | a correction deletes the line it replaces |
| `compress` | one summary line that names the lines it came from |
| `assemble` | task + pins first, fill by rank, park what does not fit |

Already written for you: the `Line` and `Context` records, both counters, the
summary-drift check (`facts_preserved`) and the poison-removal helper (`drop_source`).

## The three ways this goes wrong

**Truncating.** When a line does not fit, park it whole. A half-fact reads as a whole
fact to the model — that is how a partial invoice number becomes an invented one.

**Evicting the leash.** Pins go in before anything else, and if the pins alone exceed
the budget, that is a `BudgetError` you want to see loudly at assembly time.

**Trusting the summarizer.** Compression is a lossy write. Run `facts_preserved()`
against your summarizer with facts you know are in the transcript, and watch it fail
before you rely on it.

## Then do it for your own assistant

Wire this into the assistant and log the receipt on every step: tokens used, lines
kept, lines parked. Let it run a long task and read the log — you will see the window
fill with things that stopped mattering around step four. That log is the difference
between an agent that degrades gracefully over twenty steps and one that quietly
forgets its instructions at step twelve.
