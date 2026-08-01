# 8.3 Deploy & observe

Instrument the request path with **OpenTelemetry**, then derive P95, P99, spend by tier
and a promotion guard from the exported spans. Fill the TODOs in `src/observe.py`.

Two things to hold on to while you work:

- Use the OpenInference attribute names that are already defined at the top of the
  file. Invent your own and every dashboard you ever build is bespoke.
- Read the metrics **off the spans**. The moment latency lives in one place and traces
  in another, they disagree, and you will trust the wrong one.

The provider is wired for you with an in-memory exporter, which is why this whole layer
is testable with no collector. Remember: a deployed MCP server needs auth.
