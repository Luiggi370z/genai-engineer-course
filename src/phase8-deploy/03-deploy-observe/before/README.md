# 8.3 Deploy & observe

**Goal.** Instrument the request path with real OpenTelemetry spans — OpenInference
attribute names where a convention exists, clearly-marked custom extensions where
none does — then derive P95/P99, spend by tier, error and cache-hit rates, and a
promotion guard *off the spans*, not from a parallel bookkeeping list.
**Prerequisite.** 1.2 Token & cost meter — the token and dollar numbers you attach
to each span come from there.
**Effort.** ~60 min · moderate.

## Do this

```bash
make setup && make test     # 14 failing tests — read them, they are the spec
$EDITOR src/observe.py      # TODOs 1-10: spans, billing, metrics, promotion guard
make check                  # green: ruff + pyright + pytest, all offline
```

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

## Stuck?

1. Everything downstream reads the spans that `recorder()` collected. Latency is
   `span.end_time - span.start_time` in nanoseconds — divide by `MS_PER_NS` and
   resist keeping a second list of latencies anywhere.
2. Nearest-rank percentile: sort, then take index `ceil(p/100 * n) - 1`. For
   `emit_call`, `tracer.start_span(name, start_time=start_ns)` plus
   `span.end(end_time=start_ns + int(duration_ms * MS_PER_NS))` gives the test its
   scripted latency distribution without sleeping.

No integration lane: `InMemorySpanExporter` ships with the OTel SDK, so the
production tracing code is the code under test, fully offline. In production you
register an OTLP exporter on the same provider and change nothing in `observe.py`.
