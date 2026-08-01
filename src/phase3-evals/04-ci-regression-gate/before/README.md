# 3.4 The CI regression gate

**Goal.** Turn an eval results file into an exit code: a gate that fails on absolute-bar breaches, regressions beyond the calibrated tolerance, collapsed or vanished slices, and instrument drift — plus trajectory metrics that score what an agent did, not just what it said. This is the mechanical part that makes the previous three lessons real.
**Prerequisite.** 3.2 (the results-file shape) and 3.3 (`TOLERANCE = 0.03` comes from its calibration report).
**Effort.** ~75 min · involved

## Do this

```bash
make setup && make test      # 19 failing tests — read them, they are the spec
$EDITOR src/gate.py          # 7 TODOs: load, bars, instrument drift, regressions, diff table, main
$EDITOR src/trajectory.py    # 7 TODOs: tool-choice F1, arg accuracy, order, containment, economy
make check                   # green: ruff + pyright + pytest, all offline
make gate                    # exactly what CI runs — must pass on the shipped run
```

## What the first failure means

`test_the_shipped_run_passes_the_gate` fails first, on `Run.load` raising `NotImplementedError`. The test to read first, though, is `test_a_collapsed_slice_fails_while_the_average_still_looks_fine`: the unanswerable slice drops to 0.40 while the overall mean stays above the bar, and the gate must still fail. Note that the shipped `evals/results.json` dips 0.015 on faithfulness and passes on purpose — that dip is inside the noise floor lesson 3.3 measured, and a gate that fires on noise gets routed around.

## Done when

- [ ] `make check` is green (lint, types, fast tests).
- [ ] `make gate` exits 0 on the shipped run and 1 with readable reasons on a collapsed slice, a vanished slice, or a changed judge — an instrument change must say "re-baseline", not "regression" (`test_a_changed_judge_is_a_re_baseline_not_a_comparison`).
- [ ] `unapproved_gated_calls` names every gated tool that fired without an approval on file (`test_a_gated_tool_without_approval_is_named`) — containment is a hard check, not a score.

## Stuck?

1. Implement `Run.load` first — every gate test starts there. Then follow the module docstring's order: bars, instrument, regressions; `gate()` just concatenates the three lists of problems.
2. In `check_regressions`, compare overall and each slice against the baseline: flag drops beyond `tolerance`, mark "COLLAPSED" when a value falls under `COLLAPSE_FLOOR` from above it, and treat a slice missing from the run as "disappeared". Over in `src/trajectory.py`, `collections.Counter` and its `&` operator do the heavy lifting for `tool_choice_f1`.

No integration lane: the gate is pure logic over two JSON files and trajectory metrics compare structures, so nothing here needs a model — the judged tier belongs in CI via `ci/evals.yml`, which you copy to `.github/workflows/` in your own repo.
