# Verification stamp — `phase8-deploy`

**Last verified:** 2026-08-01
**How:** every `after/` reference passed `make check` (ruff + pyright + pytest) on this date,
and every `before/` scaffold passed lint + type with its tests failing by design.

## What the pins here are load-bearing for

| Lesson | Pin | Why it matters |
|---|---|---|
| `01-compose` | `qdrant/qdrant:v1.18.3`, `ollama/ollama:0.32.5`, `otel/opentelemetry-collector-contrib:0.157.0` | Image pins in `docker-compose.yml` and the `docker-compose.observability.yml` overlay (current on the stamp date). `:latest` means every reviewer runs a different stack — the lesson's own checks fail on it. Both app services build from `workshops/assistant/after`'s Dockerfile; the collector is overlay-only because its scratch image cannot carry a healthcheck and the base stack must stay reviewable by `src/health.py`. |
| `03-deploy-observe` | `opentelemetry-sdk>=1.30,<2` | Verified against 1.44.0. The lesson uses `TracerProvider`, `SimpleSpanProcessor` and `InMemorySpanExporter` from `opentelemetry.sdk.trace.export.in_memory_span_exporter`, plus explicit `start_time` / `end_time` on spans so latency can be scripted without sleeping. The exporter's import path has moved before; if it moves again, that is the first thing to check. `recorder()` now also reads `OTEL_EXPORTER_OTLP_ENDPOINT` and lazily attaches the OTLP exporter (`integration` group). |
| `03-deploy-observe` (release lane) | none — stdlib only | `release.py` is stdlib (`sqlite3`, `re`, `urllib`) so the entire release lane is unit-tested with no registry, no cloud account and no card. `deploy/` targets **Fly.io** and is **not live-provisioned**: the scripts are executable, gated behind `DEPLOY_LANE=fly`, and have never been run against a paid account by this repo. `flyctl` flag names are the one thing here that can drift silently, since nothing in CI exercises them — check `fly deploy --help` before trusting the script verbatim. |
| `04-cost-latency` | none in the fast tier | The offline tier is pure standard library on purpose — the embedder and the clock are injected, so nothing about the cache logic depends on a model. `fastembed>=0.4,<1` sits in the `integration` group only. |

The slow lane for this phase is `src/verify-e2e.sh`: fifteen checks that boot the
composed stack (secure + observability overlays) and prove boot, tier, a gate that
actually refuses, a container that reports the commit it was built from, grounding
with citations and streaming, a corpus that can be updated in place, cited back to
its exact text and deleted, abstention, injection containment, approval gating
bound to the approving subject, retries that apply an effect once, an MCP
round-trip, per-subject memory isolation across authenticated HTTP, recorded spans,
spans received by the external collector, degraded-but-honest operation with Qdrant
stopped, and state that survives an assistant restart. It runs the SECURE profile
rather than the zero-key demo one, because verifying the demo profile would prove
the stack works in the one configuration nobody deploys; tokens are minted inside
the container against the same ephemeral `ASSISTANT_JWT_SECRET` the run started with.
`verify-lessons.sh` never runs it. Two script lessons from that run: under `set -o pipefail`,
`compose logs | grep -q` fails even on a match (grep's early exit kills the writer
with SIGPIPE), so the collector check greps a saved log file instead; and the
durability check must PLANT a memorable turn before restarting, because memory is
deliberately selective and ordinary questions store nothing.

A full pass takes about twenty-five minutes, nearly all of it waiting on a local
model, so the script takes `--from N` and `--only N` (and `--list`, `--no-build`).
That is a debugging affordance, not a shorter suite: fix what check 12 caught and
re-prove it in two minutes instead of re-running eleven checks that already
passed. The checks share state deliberately — one corpus, one outbox, one set of
approvals, and later checks assert on what earlier ones left behind — so resuming
is only meaningful against volumes a full run has already populated, and CI runs
the whole thing.

Adding the flag immediately paid for itself by exposing two checks that had been
passing for the wrong reason. The collector check waited for the root span and
then asserted on its children against that same snapshot, which only ever worked
because a full pass generates enough traffic for the children to have arrived
already; it now waits for all three strings in one loop. And the degraded-tier
check relied on an ingest from check 4 to have populated the warm standby, which
is an **in-process** store — empty in a freshly started container regardless of
what is in Qdrant. It now establishes its own precondition, and the fact it was
hiding is worth stating plainly: restart the service while its primary is down
and the fallback has nothing to fall back to.

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
