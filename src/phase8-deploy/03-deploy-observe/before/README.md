# 8.3 Deploy & observe

**Goal.** Instrument the request path with real OpenTelemetry spans — OpenInference
attribute names where a convention exists, clearly-marked custom extensions where
none does — then derive P95/P99, spend by tier, error and cache-hit rates, and a
promotion guard *off the spans*, not from a parallel bookkeeping list. Then build
the lane that gets the code there and takes it back: immutable tags, secrets bound
by name, a smoke check that proves the *right* code is serving, and a rollback that
knows when it cannot help.
**Prerequisite.** 1.2 Token & cost meter — the token and dollar numbers you attach
to each span come from there.
**Effort.** ~90 min · moderate.

## Do this

```bash
make setup && make test     # 42 failing tests — read them, they are the spec
$EDITOR src/observe.py      # TODOs 1-10: spans, billing, metrics, promotion guard
$EDITOR src/release.py      # TODOs 1-11: tags, secrets, smoke, rollback, backups
make check                  # green: ruff + pyright + pytest, all offline
```

The `deploy/` directory is given, not yours to write: `fly.toml` is the manifest
and the three scripts are the `flyctl` commands. They contain no judgement at all
— every decision they make is a call into `release.py`. That split is the lesson.
An untested rollback trigger is one that fires for the first time during an
incident, and shell is where logic goes to never be tested.

## What the first failure means

`test_a_traced_call_emits_one_span_with_the_convention_attributes` fails because
`llm_span` and `bill` aren't built. It wants exactly one span named `llm.call`
carrying the model, tier, token counts, and cost — using the attribute constants
at the top of the file, not names invented inline — with status OK on success. Its
sibling test pins the failure path: an exception must mark the span ERROR *and
re-raise*, because observability that swallows failures is a liability.

## Done when

- [ ] `make check` is green (lint, types, fast tests).
- [ ] `percentile` is nearest-rank with `ceil`, not `round` —
      `test_percentile_rank_ties_use_ceil_not_round` pins the tie behavior.
- [ ] `safe_to_promote` blocks a build that busts the P99 budget or badly
      regresses the tail against the release in production.
- [ ] `smoke` fails a service that is healthy, correct, and running the *wrong
      commit* — `test_a_healthy_service_running_the_wrong_code_fails_the_smoke`.
- [ ] `decide` returns `halt`, not `rollback`, when the only thing behind you is
      a mutable tag. A rollback to `latest` is the appearance of a fix.

## Stuck?

1. Everything downstream reads the spans that `recorder()` collected. Latency is
   `span.end_time - span.start_time` in nanoseconds — divide by `MS_PER_NS` and
   resist keeping a second list of latencies anywhere.
2. Nearest-rank percentile: sort, then take index `ceil(p/100 * n) - 1`. For
   `emit_call`, `tracer.start_span(name, start_time=start_ns)` plus
   `span.end(end_time=start_ns + int(duration_ms * MS_PER_NS))` gives the test its
   scripted latency distribution without sleeping.
3. The `auth` probe inverts the usual polarity: it *passes* on 401. If that reads
   backwards, that is the point — healthy and wide open is the worst state a
   deploy can end in and the only one nothing else in the system complains about.
4. `backup` is `sqlite3.Connection.backup`, not `shutil.copy`. The test races a
   writer against it on purpose; a torn copy is a file you find out about at
   restore time.

No integration lane, and no cloud account either. `InMemorySpanExporter` ships
with the OTel SDK, so the production tracing code is the code under test; and
every function in `release.py` is the pure half of a step whose other half is one
`fly` command, so the whole release lane is unit-tested offline. In production you
register an OTLP exporter on the same provider and change nothing in `observe.py`.
