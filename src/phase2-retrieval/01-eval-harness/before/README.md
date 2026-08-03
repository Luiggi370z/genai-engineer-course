# 2.1 Eval harness (build this one first)

**Goal.** Build the two-tier eval harness every later phase reuses: tier 1 is
deterministic `rapidfuzz` string metrics that run on every PR, tier 2 is real
RAGAS with a pinned LLM judge. Without it, "did my retrieval change help?" is a
vibe, not a number.
**Prerequisite.** Phase 1 (you have a pipeline that returns an answer plus
contexts). This is the first lesson of Phase 2 on purpose — measure before you tune.
**Effort.** ~45 min to green on the fast tests · +25 min for the integration tier · ~80 min realistic first pass.

## Do this

```bash
make setup && make test     # 18 failing tests — read them, they are the spec
$EDITOR src/harness.py      # TODOs 1-5: load the golden set, two non-LLM metrics, dataset builder
$EDITOR src/ragas_eval.py   # TODOs 2-3 are offline: as_score and aggregate
make check                  # green: ruff + pyright + pytest, all offline
```

Fourteen of those eighteen are in `tests/test_gate.py`, and they need no judge, no
network and no `ragas` install — tier 2's arithmetic, testable on its own. Do them
alongside `harness.py`; the rest of `ragas_eval.py` (TODOs 1, 4, 5, 6) needs Ollama
and is the optional lane at the bottom of this file.

## What the first failure means

`test_golden_set_loads_with_slices` fails because `load_golden` isn't built.
It's asking you to read `evals/golden.jsonl` (one JSON dict per line) and keep
the `slice` field — `semantic` / `exact` / `unanswerable`. Slicing is the point
of the harness: a failure tells you *where* retrieval is weak, not just that it is.

## Six rows here, thirty in yours

`evals/golden.jsonl` ships **six** rows: three `semantic`, two `exact`, one
`unanswerable`. It is a fixture whose only job is to make the harness runnable while
you build it. Slices this thin cannot tell a regression apart from one unlucky
question — the unanswerable slice is a single row, so its mean is either 0.0 or 1.0.

The workbook exercise asks for **thirty** over your own corpus: 15 semantic, 10
exact-match, 5 unanswerable. Do that after `make check` is green — get the harness
working against the fixture first, then replace the fixture with questions your users
would actually type. Notice that the test asserts `len(g) >= 6` rather than `== 6`,
which is what lets you grow the set without turning the suite red.

Tier 2 below runs the same set past a real judge. Working out whether to *believe*
that judge — labelling rows yourself and measuring how often it agrees — is
calibration, and Phase 3 is where you do it.

## Done when

- [ ] `make check` is green (lint, types, fast tests).
- [ ] `test_gate_catches_a_regression` passes: a pipeline that retrieves nothing
      scores below the 0.60 context-recall bar.
- [ ] `tests/test_gate.py` is green, including the NaN case. A judge that returns
      NaN passes every threshold — `nan < 0.85` is `False` — so a gate holding one
      has stopped gating and still prints a number.
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
`ContextRecall`) once you fill the TODOs in `src/ragas_eval.py` — a pinned,
temperature-0 judge served by Ollama's OpenAI-compatible endpoint.

Use the **0.4 surface**: `ragas.metrics.collections` for the metric classes,
`ragas.llms.llm_factory` over an `openai.AsyncOpenAI` client for the judge, and
`score(...)` one row at a time. Most tutorials still show `from ragas.metrics
import Faithfulness` with `evaluate()`; that path imports, warns, and quietly
puts you on a different API from the one lesson 3.2 teaches. A test in this
lesson asserts the installed version, so the drift fails loudly.

Needs Ollama running locally — free, but the judge model is a multi-GB download
and RAGAS pulls a heavy dependency tree. Skippable: the fast tier already proves
the harness logic.
