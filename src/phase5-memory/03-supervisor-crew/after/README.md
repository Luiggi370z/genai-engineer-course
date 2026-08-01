# 5.3 Supervisor + crew — reference

A crew that earns its keep: cheaper than one big model, and provably not worse.

```bash
make setup && make test     # 13 tests, offline, deterministic
uv run python -m src.crew   # the comparison table + one run's receipt
```

```
route              cost   vs base  quality  status
frontier     $   0.0535       0%     100%  ok
tiered       $   0.0213      60%     100%  ok
all-local    $   0.0000     100%      40%  ok
```

That third row is the whole lesson. Free is not a win when 60% of the work came back
worse — and a cost table without a quality column cannot tell you that.

## Cost and quality are one number, reported together

Each `Task` names the cheapest tier that still does it justice (`min_tier`), and
`quality()` is the share of tasks routed at or above it. It stands in for your Phase 3
eval score and behaves the same way: it drops the moment a cost optimisation starts
cutting corners. Two tests hold the line —
`test_tiering_keeps_quality_while_it_saves` and
`test_the_cheapest_route_is_an_undeclared_quality_cut`.

Whatever number your own run produces is *yours*, measured on *your* task mix. Report
it next to the eval score, or it means nothing.

## Delegation is asserted, not assumed

A supervisor that quietly does the workers' jobs itself passes every output check while
defeating the entire design. So `delegated()` inspects the trace, and
`test_a_supervisor_that_does_the_work_itself_is_caught` injects exactly that failure to
prove the check works. This is the trajectory thinking from Phase 3 applied to
orchestration: the final answer being right does not make the run right.

## A worker failure is data

One exploding researcher leaves the run `partial`, records the reason per task, and
lets the writer finish its two tasks. That is `error-as-data` from Phase 4, one layer
up: a crew where any worker can take down the whole run is a crew that will.

A task kind nobody owns is the same story — an entry in `errors`, not a `KeyError`.

## The routing direction, since it gets taught backwards

Triage is the easy part: do it cheap, even free on your laptop, and escalate the
minority that earns it. Flip it only when the *planning* is what is hard — strong
orchestrator, cheap workers. The supervisor here plans once on the free tier, whatever
the task count, which is why `by_agent()` shows `supervisor=$0.0000`.

## What is simulated and what is real

`_invoke` fakes the model call from a price table, so the suite is free and
deterministic. Everything around it — routing, delegation, cost attribution, failure
containment, the two measurements — is what you would ship. Swap `_invoke` for your
Phase-1 client and this file does not otherwise change.
