# 3.1 The golden set

**Goal.** Build the checks that make an eval dataset defensible — slice coverage, near-duplicate and leakage detection, provenance — then use them to find and fix the real problems planted in `evals/golden.jsonl`. Every score you will ever quote is a property of these questions.
**Prerequisite.** Workshop 2's RAG service — this golden set is written over the kind of corpus it retrieves from.
**Effort.** ~40 min · moderate

## Do this

```bash
make setup && make test        # 10 failing tests — read them, they are the spec
$EDITOR src/dataset.py         # 9 TODOs: loaders, duplicate/leakage checks, validate(), report()
make check                     # green: ruff + pyright + pytest, all offline
uv run python -m src.dataset   # the report you'd paste into a golden-set PR
```

## What the first failure means

`test_the_shipped_golden_set_is_clean` fails first: it asserts `validate(rows, chunks) == []`, and `validate()` raises `NotImplementedError`. It is telling you the job has two halves — implement the checks in `src/dataset.py` (they are `rapidfuzz` one-liners, no model needed), then use those checks to find and fix what was planted in `evals/golden.jsonl`: a missing slice, an abstain slice too thin to mean anything, a near-duplicate question, a question pasted straight out of a chunk, and a row with no provenance.

## Done when

- [ ] `make check` is green (lint, types, fast tests).
- [ ] `validate()` returns `[]` on the shipped `evals/golden.jsonl` — you found and fixed every planted problem (`test_the_shipped_golden_set_is_clean`).
- [ ] Defects are still detected when re-planted: `test_near_duplicate_is_detected`, `test_question_copied_out_of_a_chunk_is_detected`, and `test_empty_slice_is_reported` all pass.

## Stuck?

1. Work in test order: get `load_golden` and `load_corpus` returning real objects first — most of the other failures are just the loaders not existing yet.
2. The duplicate check is `fuzz.token_set_ratio(a, b, processor=default_process)` and the leakage check is `fuzz.partial_ratio(q, chunk, processor=default_process)`, compared against `DUPLICATE_THRESHOLD` / `LEAKAGE_THRESHOLD`. The processor matters: without it, one capital letter drops a true duplicate to 89.7 and under the threshold.

No integration lane: every check is a rapidfuzz string comparison over fixtures — offline and deterministic by design, there is no model to test against.
