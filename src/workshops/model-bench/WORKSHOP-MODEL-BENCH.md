# Workshop · The model bench  (ends Phase 1)

**Effort.** ~2.5 h of focused build time · +60 min for the integration tier · ~4 h realistic first pass.

*An author's estimate, bounded by measured volume — deliverables, TODO groups, tests, brief length — and not by learner telemetry, which this course does not collect. Treat it as relative sizing, not a stopwatch.*

Your team is about to ship an extraction feature and someone asks the only question
that matters: **which model should we use?** The answers in the room are a vendor
blog post, a leaderboard nobody can reproduce, and one engineer's vibe. None of
those survive a follow-up question.

Build the thing that does. A CLI that runs **one real task** across every candidate
and reports tokens, cost and latency side by side — then ranks them on the number
that actually decides the purchase.

This is the only standalone workshop. Workshops 2 through 8 grow one continuous
assistant; this one is the foundation underneath it, and you will keep coming back
to it. Every time a later phase says "prove the cheap tier is good enough" — the
cost ladder in Phase 8, the tiered crew in Phase 5 — this is the tool that answers.

## Architecture

```
task ──► prompts()  ──┐
                      │
candidates ───────────┼──► run_bench(runner, validate) ──► BenchRun
  local / gpt-mini    │        per case:                     one Row per candidate
  gpt / local-big     │        time it · meter it · validate it
                      │                                   │
Runner (injected) ────┘                                   ▼
  live_runner  → a real OpenAI-compatible endpoint     rank() by $/success
  fake runner  → scripted replies, offline tests           │
                                                            ▼
                                            table()  human reads it
                                            to_json() CI diffs it
```

## The seam

`before/src/bench/core.py` — `cost`, `percentile`, `run_case`, `run_bench`, `rank`,
and the `Row.cost_per_success` property that decides the ordering. The dataclasses
are given; the judgement is not.

`before/src/bench/tasks.py` — `validate_invoice` and `strip_fence`.

`before/src/bench/providers.py` — `resolve` and `live_runner`, the only code in the
project allowed to import a vendor SDK.

`report.py` and `cli.py` are given whole. Column alignment is not the lesson.

## Deliverables

Three passes. **Minimum** is the walking skeleton — the smallest thing that is
really this, and a place to stop that is not quitting. **Full** is the version you
would show someone. **Stretch** is for when the full pass came easily.

### Minimum
- [ ] A provider is a **config entry, not a code path** — `Runner` is injected, and
      the fast test tier benches four candidates with zero network
- [ ] Every row reports **tokens, cost and latency**, with cost computed from the
      response's `usage` and never from a pre-flight estimate

### Full
- [ ] Each reply is **validated against a schema**, and the row reports a success
      rate rather than assuming the call worked
- [ ] Ranking is by **cost per successful parse** — a test proves a model at half the
      price that fails three cases in four is the *worse* buy
- [ ] A provider that times out or errors becomes a **row with an error**, never a
      crashed run — one dead vendor must not hide the other three
- [ ] `--json` emits the same numbers the table shows, so a bench from today can be
      **diffed against one from last month**
- [ ] The integration tier runs the identical bench against a **real local model**
      and reports what it actually costs and how often it holds the schema

## Stretch goals

- Add a **quality** column. Right now the bench measures whether the answer parses,
  not whether it is right — hand-label the expected values for your cases and report
  field accuracy next to cost. You have just built the smallest possible version of
  Phase 3, which is the honest way to discover why Phase 3 needs four lessons.
- Bench **prompt caching**. Run the same long prefix twice and read
  `cache_read_input_tokens` on the second call. If it stays zero, find what is
  changing above your cache point (`p1-c4` explains where to look).
- Add a **budget gate**: `bench run --max-cost 0.02 --min-success 0.9` exits non-zero
  when no candidate clears both bars. That is a CI gate, and Phase 8 turns it into one.

Implement the seam above. Reference and tests: `after/src/bench/`, `after/tests/`.

**Rank on the right axis or don't rank at all.** The single most common way a model
comparison lies is by sorting on price per token. Tokens are not the unit you buy —
working answers are. A bench that says "the cheap one wins" without saying how often
it fails is marketing, and you will be asked to defend it.
