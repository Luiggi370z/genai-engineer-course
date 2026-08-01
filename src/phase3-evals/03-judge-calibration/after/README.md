# 3.3 Judge calibration — reference

The lesson almost no course teaches, and the one that decides whether your eval
numbers are evidence or decoration.

```bash
make setup && make test              # all offline: fixtures, not models
uv run python -m src.calibration     # the report you keep next to your scores
```

## What the shipped fixture shows

40 rows, hand-labeled, run against a judge whose raw scores you have:

| threshold | agreement | **kappa** | judge pass rate |
|---|---|---|---|
| 0.50 (the round number) | 0.750 | **0.444** | 0.750 |
| 0.65 (swept) | 0.825 | **0.653** | 0.475 |

Agreement moves by 7 points; **kappa moves by 21** and crosses the line where gating
merges becomes defensible. That gap is the entire argument for reporting kappa: with
a 60% human pass rate, a lazy judge scores well on agreement for free.

The extreme case is in the tests — a judge that says "pass" to everything against a
90%-pass set scores `agreement 0.90, kappa 0.00`. Same rubber stamp, two very
different-looking numbers.

## Pick the threshold from the data

0.5 is a round number, not a decision. The judge has already scored every row, so
sweeping the cut point is free — `best_threshold()` does it and reports what it found.
Do this before you argue about the metric bar.

## Then read the disagreements

`disagreement_rows()` is the actual deliverable. Every disagreement is one of three
things:

1. **a bad rubric** — the judge was asked something vaguer than what you meant;
2. **a bad label** — you were wrong, which happens and is worth knowing;
3. **an ambiguous question** — it should not be in the golden set at all.

Kappa is the receipt. The reading is the work.

## The number that feeds the CI gate

`Calibration.tolerance` turns the disagreement rate into a regression tolerance:
per-row disagreement averaged over n rows shrinks like `disagreement / sqrt(n)`, so
the shipped fixture yields **0.03**. Gate wider than that — a gate that fires on
noise gets routed around, and a routed-around gate is worse than no gate because it
looks like coverage. That is exactly the tolerance lesson 3.4 uses.

## Interpretation bands

The bands in `BANDS` are the long-standing Landis & Koch convention for inter-rater
agreement — a way to decide how much to trust a second rater, not a law of nature
and not a target to congratulate yourself against. `GATING_KAPPA = 0.60` is this
course's line for "defensible as a merge gate."

## Calibration also buys you a cheaper judge

Run the free local judge and a big hosted one over the same labeled rows. If kappa
holds up, you have justified running evals on every PR at zero marginal cost — with
a written receipt for the decision. That receipt is a very good interview answer.
