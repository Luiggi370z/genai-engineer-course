# 8.2 CI

**Goal.** Build the merge gate as four independently failing checks — quality
(faithfulness ≥ 0.85 AND recall ≥ 0.80), safety (zero red-team bypasses),
latency (P99 within budget), and cost (spend within budget) — over a
version-stamped report, and wire them into the `make eval` / `make redteam` /
`make latency` / `make cost` targets the repo-root workflow calls on every PR.
**Prerequisite.** Phase 3 evals and Phase 6 red-team — they produce the numbers
this gate reads.
**Effort.** ~35 min to green on the fast tests · no integration tier · ~60 min realistic first pass.

## Do this

```bash
make setup && make test     # failing tests — read them, they are the spec
$EDITOR src/gate.py         # fill TODOs 1-5: the four gates + should_merge
make check                  # green: ruff + pyright + pytest, all offline
make eval && make redteam && make latency && make cost   # what CI runs
make prove-gates            # every seeded regression must BLOCK
```

## What the first failure means

`test_clean_report_merges` fails because `should_merge` isn't built: a stamped
report clearing every bar must return `(True, [])`. The test that carries the
design lesson is `test_the_four_gates_fail_independently` — a safety bypass must
be invisible to the quality gate, a latency blowout to the cost gate, and so on,
which is exactly why `.github/workflows/ci.yml` at the REPO ROOT (the only path
GitHub reads; a workflow file inside a lesson folder is a file, not a build) runs
them as separate steps instead of one averaged score. `stamped` is given: a
report missing its model/prompt/corpus/dataset stamps blocks every gate, because
"faithfulness 0.91" from an unknown setup is not evidence. The CLI at the bottom
of `gate.py` is given; once your five functions work, all four make targets work.

## Done when

- [ ] `make check` is green (lint, types, fast tests).
- [ ] A faithfulness or recall regression blocks with a reason naming the metric
      and the bar (the tests grep for it).
- [ ] One red-team bypass blocks the merge even with faithfulness 0.95.
- [ ] A P99 or cost blowout blocks on its own gate and no other.
- [ ] An unstamped report blocks every gate.
- [ ] `make eval`, `make redteam`, `make latency`, `make cost` all exit 0 on the
      committed `evals/report.json`, and `make prove-gates` shows every seeded
      regression blocked.

## The same idiom applied to code

`make defect-lab` in `workshops/assistant/after` seeds regressions into the
*implementation* rather than into a report: three vulnerabilities the capstone
actually shipped, kept as running variants, with regression tests that must pass
against the fix and fail against each defect. Do it after this lesson —
`WORKSHOP-DEFECT-LAB.md` is the brief.

## Stuck?

1. Each gate returns a list of reason strings; empty list == pass. Start each
   gate with `reasons = stamped(report)` and append.
2. Compare against the `*_BAR` / `*_BUDGET_*` constants at the top of the file,
   and make sure the bypass reason contains the word "bypass", the latency
   reason "p99", the cost reason "cost" — the tests match on substrings.
3. `should_merge` concatenates all four gates' reasons but should not repeat the
   version-stamp reason four times — dedupe as you extend.

No integration lane: the gate is pure logic over a report dataclass.

`evals/report.json` is a fixture, and you should be suspicious of it. It makes
the policy testable in one lesson with no stack booted, and it is also the exact
anti-pattern this phase warns about: a gate reading a committed number checks
that somebody edited a file, not that the system still works. The root workflow's
`evidence` job is the honest version — it builds the capstone image, runs
`python -m assistant.report` inside it, and points this same CLI at the report
that run produced. Try it: `make gate` in `workshops/assistant/after`.
