# 2.1 Eval harness (build this one first)

**Goal.** Build the two-tier eval harness every later phase reuses: tier 1 is
deterministic `rapidfuzz` string metrics that run on every PR, tier 2 is real
RAGAS with a pinned LLM judge. Without it, "did my retrieval change help?" is a
vibe, not a number.
**Prerequisite.** Phase 1 (you have a pipeline that returns an answer plus
contexts). This is the first lesson of Phase 2 on purpose — measure before you tune.
**Effort.** ~45 min · moderate.

## Do this

```bash
make setup && make test     # 4 failing tests — read them, they are the spec
$EDITOR src/harness.py      # TODOs 1-5: load the golden set, two non-LLM metrics, dataset builder
make check                  # green: ruff + pyright + pytest, all offline
```

## What the first failure means

`test_golden_set_loads_with_slices` fails because `load_golden` isn't built.
It's asking you to read `evals/golden.jsonl` (one JSON dict per line) and keep
the `slice` field — `semantic` / `exact` / `unanswerable`. Slicing is the point
of the harness: a failure tells you *where* retrieval is weak, not just that it is.

## Done when

- [ ] `make check` is green (lint, types, fast tests).
- [ ] `test_gate_catches_a_regression` passes: a pipeline that retrieves nothing
      scores below the 0.60 context-recall bar.
- [ ] The metrics keep their honest `*_nonllm` names — they measure lexical
      similarity, never report them as faithfulness.

## Stuck?

1. Each metric is one library call, not an algorithm. Both compare two strings
   and return 0..1; `evaluate_nonllm` just averages each metric across rows.
2. `fuzz.token_set_ratio(a, b)` returns 0..100 — scale it to 0..1.
   `context_recall_nonllm` is the *best* score of any retrieved context against
   the ground truth, and 0.0 when nothing was retrieved.

## Going further (optional integration lane)
`make test-integration` runs the real RAGAS metrics (`Faithfulness`,
`LLMContextRecall`) once you fill the three TODOs in `src/ragas_eval.py` — a
pinned, temperature-0 judge served by Ollama's OpenAI-compatible endpoint. Needs
Ollama running locally — free, but the judge model is a multi-GB download and
RAGAS pulls a heavy dependency tree. Skippable: the fast tier already proves the
harness logic.
