# 5.3 Supervisor + crew

Build a crew that is cheaper than a single frontier model — and prove it did not get
worse in the process.

```bash
make setup && make test     # 13 failures; the failures are the spec
uv run python -m src.crew   # the table you're working toward
```

## Your job

In `src/crew.py`:

| Function | The interesting part |
|---|---|
| `worker` | attribute the call to the agent that *owns* the kind, not the supervisor |
| `run` | one supervisor call, delegate the rest, catch worker failures as data |
| `quality` | share of tasks routed at or above their `min_tier` |
| `delegated` | did the supervisor hand the work over, or keep it? |

Given: the records, the three routers, `_invoke` (the simulated model call), and the
reporting helpers.

## The three failures the tests are looking for

**Cheap and worse.** `cheapest_route` sends everything to the free tier. It must come
out cheapest *and* below 100% quality — a cost win you would have to declare as a
quality cut. If your `quality()` cannot see it, it is not measuring anything.

**A supervisor that hoards.** One test injects a worker that attributes its call to the
supervisor. `delegated()` has to catch it. An agent that answers everything itself
looks perfect in the output and wastes the whole architecture.

**A worker that explodes.** A `TimeoutError` from the researcher leaves the run
`partial` with reasons recorded, and the writer still finishes its tasks.

## Then do it for real

Replace `_invoke` with your Phase-1 client, run your own task mix both ways, and put
the table in your repo next to the Phase-3 eval score. The number you get is yours —
which is the only kind of cost number worth quoting in an interview.
