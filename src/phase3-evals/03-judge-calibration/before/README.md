# 3.3 Judge calibration

**Goal.** Measure how much your judge deserves to be trusted: compare its verdicts against 40 rows you hand-labeled, report kappa instead of raw agreement, sweep the decision threshold, and derive the regression tolerance that lesson 3.4's CI gate will use.
**Prerequisite.** 3.2 — the judge scores in `evals/labeled.jsonl` are the kind of output that harness produces.
**Effort.** ~45 min to green on the fast tests · no integration tier · ~75 min realistic first pass.

## Do this

```bash
make setup && make test            # 12 failing tests — read them, they are the spec
$EDITOR src/calibration.py         # 9 TODOs: agreement, kappa, threshold sweep, tolerance, report
make check                         # green: ruff + pyright + pytest, all offline
uv run python -m src.calibration   # the report you keep next to your scores
```

## What the first failure means

`test_the_labeled_set_is_big_enough_and_carries_provenance` fails first, on `load_labeled` raising `NotImplementedError`. The test that carries the lesson is `test_a_rubber_stamp_judge_has_high_agreement_and_no_kappa`: a judge that says "pass" to everything, scored against a 90%-pass set, must come out as agreement 0.90 and kappa 0.00 — same rubber stamp, two very different-looking numbers, and the whole reason kappa is the number you report.

## Done when

- [ ] `make check` is green (lint, types, fast tests).
- [ ] Sweeping the threshold beats the default 0.5 and makes the shipped judge gatable (`test_the_shipped_judge_only_becomes_gatable_after_calibration`).
- [ ] `tolerance` is derived from the disagreement rate — `(1 - agreement) / sqrt(n)`, floored at 0.01 — not guessed (`test_tolerance_comes_from_the_disagreement_rate`).

## Stuck?

1. Start with `load_labeled` and `verdicts` — everything else consumes their output, and `calibrate` is mostly bookkeeping around them.
2. Do not hand-roll the statistic: `sklearn.metrics.cohen_kappa_score(human, judge, labels=["pass", "fail"])`. For `best_threshold`, call `calibrate` at each step of the sweep and keep the result with the highest kappa — the judge already scored every row, so sweeping costs nothing.

No integration lane: the judge's raw scores are already recorded in `evals/labeled.jsonl`, so calibration is pure statistics over fixtures — no model needed.
