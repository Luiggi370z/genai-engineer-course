# 8.3 Deploy & observe — reference

Real OpenTelemetry spans carrying OpenInference attribute names where a convention
exists (`llm.model_name`, `llm.token_count.*`) and clearly-marked custom extensions
where none does (`cost.usd`, `llm.tier`, `cache.hit`), with P95/P99, spend by tier
and a rollback guard all read **off the spans** rather than from a parallel
bookkeeping list.

`InMemorySpanExporter` ships with the SDK, so the production tracing code is the code
under test — no collector, no vendor account. Swap in an OTLP exporter and nothing in
`observe.py` changes:

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=https://cloud.langfuse.com/api/public/otel   # Langfuse v4
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:6006/v1/traces              # local Phoenix
```

Deploy notes: secrets via the platform's secret manager (never the image), a `/health`
endpoint, keep the previous image for one-click rollback, and turn ON the MCP server's
auth (Phase 7) the moment it is remote.

## Concept → framework primitive

| what you built | the primitive in the OpenTelemetry SDK | what OTel adds |
|---|---|---|
| `recorder()`'s manual wiring of a tracer + exporter | `TracerProvider()` + `provider.get_tracer(service)` | a standard, swappable provider any OTel-aware vendor can attach to |
| `Recorder.spans()` reading a list you kept yourself | `InMemorySpanExporter` + `SimpleSpanProcessor` (`exporter.get_finished_spans()`) | a real exporter interface — swap in `BatchSpanProcessor(OTLPSpanExporter(...))` and nothing else in `observe.py` changes |
| `llm_span()`'s try/except around a block | `tracer.start_as_current_span()` + `Status(StatusCode.OK)` / `Status(StatusCode.ERROR, ...)` | error and status semantics every OTel-compatible backend already understands |
| `emit_call()`'s manual start/end timestamps | `tracer.start_span(..., start_time=...)` / `span.end(end_time=...)` | nanosecond-precision timing built into the span model itself |
| `p50` / `p95` / `p99` / `cost_of` / `error_rate` reading off spans | `ReadableSpan.attributes`, `.start_time` / `.end_time`, `.status.status_code` | metrics derived from the same trace data a dashboard or vendor also reads — one source of truth |
| `MODEL` / `PROMPT_TOKENS` / `COMPLETION_TOKENS` constants | OpenInference semantic-convention names (`llm.model_name`, `llm.token_count.*`) | a shared vocabulary that Phoenix, Langfuse, and other OTel-native tools already render without touching this repo |
| `COST` / `TIER` / `CACHE_HIT` constants | plain custom span attributes — no convention covers them | nothing; these stay your own extension, and the point is knowing the difference |

**Two artifacts.** You now own two things that prove different skills: `observe.py`
proves you understand what a span actually carries and how P95/spend/error-rate
are derived from it rather than tracked separately, and the `integration`
dependency group's `OTLPSpanExporter` proves you can point that exact same
provider at Langfuse or Phoenix in production without touching a line of
tracing code. The interview skill is naming which attributes are OpenInference
convention and which are yours — this table is that answer, spelled out.
