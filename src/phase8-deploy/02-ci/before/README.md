# 8.2 CI

**Goal.** Build the merge gate as two independently failing checks — quality
(faithfulness ≥ 0.85 AND recall ≥ 0.80) and safety (zero red-team bypasses) — and
wire them into the `make eval` / `make redteam` targets a GitHub Actions workflow
calls on every PR.
**Prerequisite.** Phase 3 evals and Phase 6 red-team — they produce the numbers
this gate reads.
**Effort.** ~25 min · gentle.

## Do this

```bash
make setup && make test     # 5 failing tests — read them, they are the spec
$EDITOR src/gate.py         # fill TODOs 1-3: quality_ok, safety_ok, should_merge
make check                  # green: ruff + pyright + pytest, all offline
make eval && make redteam   # the exact commands CI runs, now passing locally
```

## What the first failure means

`test_clean_report_merges` fails because `should_merge` isn't built: a report
clearing both bars with zero bypasses must return `(True, [])`. The test that
carries the design lesson is `test_the_two_gates_fail_independently` — a safety
bypass must be invisible to the quality gate and vice versa, which is exactly why
the committed `.github/workflows/ci.yml` runs them as two required jobs instead of
one averaged score. The CLI at the bottom of `gate.py` is given; once your three
functions work, `make eval` and `make redteam` work.

## Done when

- [ ] `make check` is green (lint, types, fast tests).
- [ ] A faithfulness or recall regression blocks with a reason naming the metric
      and the bar (the tests grep for it).
- [ ] One red-team bypass blocks the merge even with faithfulness 0.95.
- [ ] `make eval` and `make redteam` both exit 0 on the committed
      `evals/report.json`.

## Stuck?

1. Each gate returns a list of reason strings; empty list == pass. `should_merge`
   is then just both lists concatenated and `reasons == []`.
2. Compare against the `FAITHFULNESS_BAR` and `RECALL_BAR` constants at the top of
   the file, and make sure the bypass reason contains the word "bypass" — the
   tests match on substrings.

No integration lane: the gate is pure logic over a report dataclass. In your own
repo, point the two targets at the capstone's eval suite and red-team fixture
instead of a committed report — the workflow does not change.
