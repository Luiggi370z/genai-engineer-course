# Verification stamp — `phase8-deploy`

**Last verified:** 2026-08-01
**How:** every `after/` reference passed `make check` (ruff + pyright + pytest) on this date,
and every `before/` scaffold passed lint + type with its tests failing by design.

## What the pins here are load-bearing for

| Lesson | Pin | Why it matters |
|---|---|---|
| `01-compose` | `qdrant/qdrant:v1.18.3`, `ollama/ollama:0.32.5`, `otel/opentelemetry-collector-contrib:0.157.0` | Image pins in `docker-compose.yml` and the `docker-compose.observability.yml` overlay (current on the stamp date). `:latest` means every reviewer runs a different stack — the lesson's own checks fail on it. Both app services build from `workshops/assistant/after`'s Dockerfile; the collector is overlay-only because its scratch image cannot carry a healthcheck and the base stack must stay reviewable by `src/health.py`. |
| `03-deploy-observe` | `opentelemetry-sdk>=1.30,<2` | Verified against 1.44.0. The lesson uses `TracerProvider`, `SimpleSpanProcessor` and `InMemorySpanExporter` from `opentelemetry.sdk.trace.export.in_memory_span_exporter`, plus explicit `start_time` / `end_time` on spans so latency can be scripted without sleeping. The exporter's import path has moved before; if it moves again, that is the first thing to check. `recorder()` now also reads `OTEL_EXPORTER_OTLP_ENDPOINT` and lazily attaches the OTLP exporter (`integration` group). |
| `04-cost-latency` | none in the fast tier | The offline tier is pure standard library on purpose — the embedder and the clock are injected, so nothing about the cache logic depends on a model. `fastembed>=0.4,<1` sits in the `integration` group only. |

The slow lane for this phase is `src/verify-e2e.sh`: eleven checks that boot the
composed stack (with the observability overlay) and prove boot, tier, grounding with
citations and streaming, abstention, injection containment, approval gating, an MCP
round-trip, recorded spans, spans received by the external collector, degraded-but-
honest operation with Qdrant stopped, and state that survives an assistant restart.
`verify-lessons.sh` never runs it. All eleven passed against the real stack on the
stamp date. Two script lessons from that run: under `set -o pipefail`,
`compose logs | grep -q` fails even on a match (grep's early exit kills the writer
with SIGPIPE), so the collector check greps a saved log file instead; and the
durability check must PLANT a memorable turn before restarting, because memory is
deliberately selective and ordinary questions store nothing.

The observability layer is deliberately vendor-free: no Langfuse or Phoenix SDK is
imported anywhere. Both read OTLP, so the backend is an environment variable and there
is no vendor dependency to pin or to break.

## Why this file exists

GenAI libraries move fast enough to break a course between readings. On 2026-07-28 the
MCP Python SDK shipped v2 and **removed** `mcp.server.fastmcp` — an unpinned install
broke every v1 example overnight.

So: **every dependency in this repo carries an upper bound**, e.g. `mcp>=2.0.0,<3`.
Caps are raised deliberately, never by accident. If a lesson fails to install:

1. Check this date. If it's old, expect drift.
2. Read the lesson's `pyproject.toml` — the pin tells you what it was built against.
3. Upgrade one dependency at a time and re-run `make check`.

Pinning-with-intent is itself part of the curriculum.
