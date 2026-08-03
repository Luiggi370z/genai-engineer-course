# 5.3 Supervisor + crew

**Goal.** Build a supervisor-and-workers crew on tiered models and prove the cost
claim honestly: every run reports cost and quality together, so "cheaper" cannot
quietly mean "worse".
**Prerequisite.** 5.2 Context engineering, plus the error-as-data habit from Phase 4.
**Effort.** ~45 min to green on the fast tests · no integration tier · ~75 min realistic first pass.

## Do this

```bash
make setup && make test   # 13 failing tests — read them, they are the spec
$EDITOR src/crew.py       # fill worker, run, quality, delegated
make check                # green: ruff + pyright + pytest, all offline
uv run python -m src.crew # the comparison table you are working toward
```

## What the first failure means

`test_tiering_is_cheaper_than_the_single_model_baseline` fails because `run()` and
`worker()` aren't built yet. It's asking for the delegation loop: the supervisor
plans exactly once on the free tier, then hands each task to the worker that owns
its kind (`SKILLS`), on the tier the router chose. Cost falls out of the recorded
calls — the loop is what you're building, the arithmetic is given.

## Done when

- [ ] `make check` is green (lint, types, fast tests).
- [ ] `quality()` exposes the all-local route as cheapest *and* below 100% quality —
      `test_the_cheapest_route_is_an_undeclared_quality_cut` is the test that says
      cheap-and-worse out loud.
- [ ] An exploding researcher leaves the run `partial` with reasons in `crew.errors`
      while the writer still finishes its tasks
      (`test_one_exploding_worker_does_not_sink_the_run`).

## Stuck?

1. `worker()` is one `_invoke`, attributed to `SKILLS[task.kind]` — not to the
   supervisor. That attribution is exactly what `delegated()` inspects, and one test
   injects a hoarding worker to prove the check works.
2. In `run()`, catch anything a worker raises into `crew.errors[task.id]` instead of
   letting it propagate, and treat a kind nobody owns the same way ("no worker
   owns..."), not as a `KeyError`. `quality()` maps `task_id -> tier` from the
   calls and counts tasks whose `TIERS` index is at or above their `min_tier` —
   with no tasks scoring 1.0, not a `ZeroDivisionError`.

No integration lane: model calls are simulated from a price table (`_invoke`), so
the whole suite is offline and deterministic — swap `_invoke` for your Phase-1
client when you want real numbers on your own task mix.
