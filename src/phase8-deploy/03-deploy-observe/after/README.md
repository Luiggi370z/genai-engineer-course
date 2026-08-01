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
