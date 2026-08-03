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

A full pass is dominated by the local model, so the script takes `--from N` and
`--only N` (and `--list`, `--no-build`, `--host-model`).
That is a debugging affordance, not a shorter suite: fix what check 12 caught and
re-prove it in two minutes instead of re-running eleven checks that already
passed. The checks share state deliberately — one corpus, one outbox, one set of
approvals, and later checks assert on what earlier ones left behind — so resuming
is only meaningful against volumes a full run has already populated. Every lane
that reports a result runs the whole thing: push CI builds the image and
validates the compose files without booting the stack, and the scheduled `e2e`
workflow runs all of it with `--ci`.

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

### The twenty minutes, and what was hiding inside them

The run used to take about twenty-five minutes, and roughly seventeen of those were
one thing: the composer asking for an unbounded completion, waiting out its 60-second
budget, retrying once, and answering from the offline composer instead. Every check
passed the whole time, and that is the part worth sitting with rather than the clock:
nothing was broken, the answers were grounded, `/health` was green, and **the model
was never the one answering**. The suite asked "is this answer grounded in the
corpus", which the fallback composer also satisfies, and never asked "did the model
write it". It is forty-five seconds now with `--host-model`, and twelve minutes on
the self-contained lane — the twenty-five became twelve by spending it generating
rather than timing out, with the model composing in both.

The second half of that took another failed run to see. Bounding the completion cut
the work; it did not make the work fit, because 60 seconds was never a budget this
lane could meet — 0.52 tokens/second and a hundred tokens of answer is three minutes
whatever you do to the prompt. So every composition still timed out, the fallback
still answered, and check 4 — now that it asserts the model composed — failed the
whole run on a stack with nothing wrong with it. The budget moved out of the library
and into the deployment that knows its own hardware: `COMPOSE_TIMEOUT_SECONDS`, set
to fifteen minutes in `docker-compose.yml` and back to sixty seconds in the
host-model overlay. A constant that is correct behind a GPU and absurd without one
is a configuration item wearing a constant's clothes.

Raising it exposed the third one, which was the same mistake at a different layer.
The secure overlay caps the whole request at `REQUEST_DEADLINE_SECONDS`, and
`deadline.capped` hands a call the tighter of the two clocks — so a 120-second
request budget silently overruled the 900-second composition budget that had just
been set for it. Two numbers describing nested spans of time, tuned independently,
which is a thing that stays correct only by accident. Worse, the stream failed
differently from the batch path: `/ask/stream` broke out of its loop on an expired
deadline without a final frame, so the client got chunks and then nothing — a
truncated answer that looks exactly like a finished one. The deadline is now
sixteen minutes on that lane, and every way the stream can end ends in a `done`
frame that says which way it was.

Two fixes, in the order they matter. The composer now asks for a **bounded**
completion — `think=False` and a `num_predict` ceiling (`adapters.py`). A reasoning
model deliberates hardest about a task with nothing to work out: measured at 667
reasoning tokens for a one-sentence restatement of retrieved text, at 0.52
tokens/second, which does not fit in any budget. The same prompt with thinking off:
10 tokens. A token cap alone would not have helped — cap it with thinking on and the
model spends the cap thinking and returns nothing. And check 4 now **asserts the
model composed the answer**, by reading `degraded.brain` off `/health` after the ask.
That assertion is the durable half of the fix; the timeout tuning is not.

The 0.52 tokens/second is itself a fact about deployment rather than about this
laptop: Docker Desktop on macOS gives containers **no GPU**, so the in-stack Ollama
runs a 9B model on CPU inside a VM. The host's own Ollama, same model, same machine,
with Metal: 81 tokens/second — 156×. `--host-model` and `docker-compose.hostmodel.yml`
point the container at it through `host.docker.internal` and switch the in-stack
service off with an unenabled profile, which also makes the overlay the smallest real
use of `!override` in the repo (the base file's `depends_on` waits for a service the
overlay has just turned off). The default lane stays self-contained, because check 1's
claim is one command with nothing installed — and it is the self-contained lane the
scheduled workflow runs, on a smaller model, so the claim is exercised rather than
asserted.

What the bounded composer did not rescue, on the CPU lane, is everything after the
first few checks. Check 4 composes with a freshly loaded model and an idle machine and
now makes its budget reliably; by check 10 the same call has started exceeding 60
seconds again, because an abandoned generation does not stop when the client gives up
— Ollama was still burning 395% CPU on work nobody was waiting for, and each later
call queues behind that. A timeout is a promise to the caller, not a cancellation of
the work. If you take one operational lesson from this phase, that is a good candidate.

The **streaming** path is the sharper version of the same problem, and there it is
structural rather than contention. `tier.stream` is safe-buffered — the gate screens
the entire answer before releasing the first chunk — so a first-chunk deadline is
really a whole-generation deadline, on a generation the batch path has already paid
for once. Check 4 therefore holds the two paths to different standards: a batch
fallback fails the run, a stream fallback is allowed but must appear on `/health`
naming the stream. "Allowed to degrade, not allowed to be quiet about it" is the
contract the service makes to its callers, applied to its own verifier.

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
