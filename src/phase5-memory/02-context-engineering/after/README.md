# 5.2 Context engineering — reference

The window is a budget. This is how you spend it on purpose.

```bash
make setup && make test        # 13 tests, offline, no tokenizer download
uv run python -m src.context   # the receipt: tokens, lines, pinned, parked
make test-integration          # the same budget, counted with the real tokenizer
```

## The four moves

| Move | Applied to | The price |
|---|---|---|
| **keep** (pin) | guardrails, the goal, this step's inputs | tokens on every turn — pin sparingly |
| **compress** | finished turns, long tool output | lossy; summary drift is a real bug |
| **evict** | whatever a newer line supersedes | unrecoverable unless you parked it |
| **park** | documents, transcripts, bulk | a recall round-trip and the risk of a miss |

`assemble()` applies them in that order, and the order is the design: the task and the
pins go in first, so if they alone exceed the budget you get a `BudgetError` instead of
an agent that silently lost its own instructions.

## Three invariants worth a test each

**Never over budget.** `test_assembly_never_exceeds_the_budget` — the cap is arithmetic,
not a suggestion.

**Never truncate.** A line that does not fit is parked *whole*. Half a fact reads as a
whole fact to the model, which is how "the total is 41,9" becomes a number it will
happily complete for you.

**Pins survive pressure.** If budget pressure can evict your guardrails, your leash is
decorative.

## Provenance is the anti-poisoning mechanism

Every `Line` carries a `source`, and `render()` puts it in the prompt:

```
[policy] Never send email without explicit approval
[turn-3] Lu works in UTC-5 and prefers meetings after 10:00
```

That is what makes `context.from_source("tool-call-7")` possible — and `drop_source`
after it. Without provenance, "the agent said something weird" is unfalsifiable; with
it, the bad claim has an address. Compression is where poison most often enters,
because a summary turns a guess into a statement, so the summary line records the ids
it was made from.

## The summarizer is a component, so test it

`facts_preserved()` is deliberately trivial, and `test_the_summarizer_check_catches_a_dropped_fact`
runs it twice: once against an honest summarizer (empty list) and once against a lossy
one (all three facts reported missing). A check you have never seen fail is not a check.

## Two counters, on purpose

`word_counter` is deterministic, offline, and does not pretend to be a tokenizer:
it keeps the fast tier hermetic. `tiktoken_counter()` is the real encoding and runs in
the integration tier, because `get_encoding` downloads a BPE file on first use — and a
fast tier that needs the network is not a fast tier. Anywhere the count decides what
you spend, use the real one.
