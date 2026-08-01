# 3.4 The CI regression gate — reference

```bash
make setup && make test    # the gate logic, offline
make gate                  # exactly what CI runs
```

## Four checks, because they catch four different bugs

| Check | Catches | What a bar-only gate would do |
|---|---|---|
| Absolute bars | a system that simply isn't good enough | — |
| Regression vs baseline | **slow rot**: 0.94 → 0.86, one green PR at a time | let it through |
| Per-slice regression | the collapsed slice an average hides | let it through |
| Instrument drift | comparing a new judge's numbers to an old judge's | call it a regression |

`test_a_collapsed_slice_fails_while_the_average_still_looks_fine` is the one to read
first: the unanswerable slice falls from 1.00 to 0.40, the overall mean stays above
the bar, and the gate still fails. That is the entire reason results are sliced.

## The tolerance is calibrated, not chosen

`TOLERANCE = 0.03` comes from lesson 3.3 — the judge's disagreement rate with your own
labels, averaged over the suite. Recompute it when you re-calibrate.

Gating tighter than your noise floor is how a gate loses its authority: it fires on
nothing, someone adds `--no-verify` to their muscle memory, and now you have a gate
that gates nothing. The shipped run dips 0.015 on faithfulness and **passes on
purpose**.

## Instrument drift is a re-baseline, not a regression

Every results file records the judge model, its temperature, the endpoint and the
RAGAS version. If any of those changed, the gate refuses to compare and says so:

```
gate FAILED:
  - the instrument changed, so these numbers are not comparable
    (judge_model: 'qwen3-coder:30b' -> 'some-other-model:70b') — re-baseline
    deliberately, in a reviewed commit
```

That message is the point. Silently re-baselining after a judge swap is how a
dashboard starts lying.

## The failure message is a code-review artifact

`diff_table()` prints base / now / delta / status per metric and per slice, so the
reviewer sees *which slice moved* without checking out the branch. A gate whose
output is a stack trace gets ignored; a gate whose output is a table gets read.

## Two tiers in the workflow

`ci/evals.yml` (copy it to `.github/workflows/` in your own repo) runs the fast tier
on every pull request and the judged tier nightly. If the judged tier gated every PR,
someone would eventually make it optional — and then it would gate nothing.

Re-baselining stays human: run the judged suite, review the diff, commit
`evals/baseline.json` in its own PR with a note about why the number moved. **A gate
that updates its own baseline is a gate that never fails.**
