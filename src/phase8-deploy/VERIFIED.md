# Verification stamp — `phase8-deploy`

**Last verified:** 2026-08-02
**How:** every `after/` reference passed `make check` (ruff + pyright + pytest) on this date,
and every `before/` scaffold passed lint + type with its tests failing by design.

**What this stamp pins — and what it does not.** Ranges, not versions. Every lesson's
`pyproject.toml` declares upper-bounded *ranges* (`ragas>=0.4,<0.5`), so a fresh
`uv sync` resolves the newest release inside the range, which is usually — not
necessarily — what the date above was taken against. Where this file names an exact
version, that is a **record** of what the verified run resolved to, not a constraint
that reinstalls it. Exactly one lockfile is tracked in the whole repo,
`workshops/assistant/after/uv.lock`: the capstone's Python tree is the only one fixed by
hash rather than by range, because it is the only one that gets deployed. That still is
not a bit-reproducible image — its Dockerfile bases are floating tags and the stack
pulls its models by tag, both deliberately, so a rebuild picks up Debian's security
patches instead of pinning a known-vulnerable layer. Everything else is version-bounded.
Interpreter: **3.11 through 3.14** (`>=3.11,<3.15`), with both ends run in CI on every
push; `phase4-agents/04-framework-bakeoff` pins 3.12 and says so itself. The long version is in [`../README.md`](../README.md).

## What the pins here are load-bearing for

| Lesson | Pin | Why it matters |
|---|---|---|
| `01-compose` | `qdrant/qdrant:v1.18.3`, `otel/opentelemetry-collector-contrib:0.157.0`, `quay.io/keycloak/keycloak:26.5.2` — each with the `@sha256:` digest that tag resolved to on the stamp date | Image pins in `docker-compose.yml` and the `observability` and `oauth` overlays. `:latest` means every reviewer runs a different stack — the lesson's own checks fail on it — and a version tag only narrows that, since a tag is a mutable pointer its publisher can repoint at a rebuild. The digests are multi-arch index digests, so the same line resolves on an ARM laptop and an x86 runner. Both app services build from `workshops/assistant/after`'s Dockerfile; the collector is overlay-only because its scratch image cannot carry a healthcheck and the base stack must stay reviewable by `src/health.py`. |
| `01-compose` (the model) | not pinned by compose at all — `qwen3.5:9b` and `nomic-embed-text` live on the host | Docker Desktop passes no GPU to containers, so the model runs outside the stack and the assistant reaches it at `host.docker.internal:11434`. The pin moves with it: `preflight-ollama.sh --json` records the Ollama version and both model **digests**, and `verify-e2e.sh` folds them into its attestation, so a release names the bytes that answered even though no compose line does. |
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
`--only N` (and `--list`, `--no-build`).
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

### What a grep over the whole response cannot see (2026-08-02)

Third time these checks have been caught passing for the wrong reason, and this one
was a single habit repeated twenty times: `curl ... | grep -qi reimburse`. The
response body carries `answer`, `contexts`, `citations`, `memories` and `grounding`,
so a grep for a word matches when the word is in a *retrieved context* and the
assistant said "I don't know". Check 4 reported success for two audit rounds while
the capstone's composer was discarding the very hit the embedder had just found. The
check was measuring retrieval and reporting it as an answer.

Assertions now go through `answer_says`, `grounded_in` and `cites`, which read one
JSON field each, and every remaining whole-body `grep` is a *negative* assertion —
where scanning everything is the point, and where the comment now says so.
Positive claims about what a user sees must name the field the user sees. The
semantic-recall check additionally prints the top citation's `score` and
`scored_by`, since a relevance floor nobody can read is a number nobody will retune.

`ASSISTANT_MIN_SCORE: "0.58"` is now in the base `docker-compose.yml`, measured
against this corpus and `nomic-embed-text` (synonym-only true positive 0.6596; best
off-topic neighbour 0.5097). Both numbers move with the corpus and the embedder,
which is why the value sits in the compose file beside the measurement and not in
the library.

That floor governs the **dense** arm only. It was briefly applied to every fused
candidate, which is a different thing and quietly turned hybrid retrieval back into
dense retrieval: an exact search for `ZX-99417` returned nothing, because the one
document containing it scored 0.535 by cosine while being the sole hit on a sparse
arm that had no doubt at all. A sparse candidate is now admitted by its own rule —
a distinctive query term, one carrying a digit or written in caps, appearing in the
document verbatim — which needs no calibration and cannot be faked by prose. Either
arm can admit a candidate; neither can veto one. The rule stays narrow deliberately:
admitting on any shared word would restore the round-4 failure from the other side.

The release lane also runs from `docker compose down -v` into its own
`QDRANT_COLLECTION`, because release numbers measured over whatever eleven earlier
checks happened to ingest are numbers about the test run.

### The twenty minutes, and what was hiding inside them

The run used to take about twenty-five minutes, and roughly seventeen of those were
one thing: the composer asking for an unbounded completion, waiting out its 60-second
budget, retrying once, and answering from the offline composer instead. Every check
passed the whole time, and that is the part worth sitting with rather than the clock:
nothing was broken, the answers were grounded, `/health` was green, and **the model
was never the one answering**. The suite asked "is this answer grounded in the
corpus", which the fallback composer also satisfies, and never asked "did the model
write it". It is forty-five seconds now, with the model composing every answer.

The second half of that took another failed run to see. Bounding the completion cut
the work; it did not make the work fit, because 60 seconds was never a budget this
lane could meet — 0.52 tokens/second and a hundred tokens of answer is three minutes
whatever you do to the prompt. So every composition still timed out, the fallback
still answered, and check 4 — now that it asserts the model composed — failed the
whole run on a stack with nothing wrong with it. The budget moved out of the library
and into the deployment that knows its own hardware: `COMPOSE_TIMEOUT_SECONDS`,
fifteen minutes while the model was in a container and sixty seconds now that it is
not. A constant that is correct behind a GPU and absurd without one is a
configuration item wearing a constant's clothes — which is why the setting survived
the topology change that made its original value unnecessary.

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
laptop: Docker Desktop on macOS gives containers **no GPU**, so a containerised
Ollama runs a 9B model on CPU inside a VM. The host's own Ollama, same model, same
machine, with Metal: 81 tokens/second — 156×.

That number eventually decided the topology. The stack shipped a containerised
Ollama for as long as it did because of a claim worth wanting — "one command,
nothing installed, no keys" — and the claim was true; it was just true about a
configuration in which the model could not answer within any reasonable budget.
Two lanes were maintained in parallel for a while, which is the usual way a project
avoids choosing. The choice, when it came, was to keep the honest half: infrastructure
in compose, model on the host, `host.docker.internal:11434` between them, one lane.
What "one command" cost to give up was small — `ollama serve` and two pulls — and
what it bought was a suite where every check runs against the model that will
actually serve users, in forty-five seconds instead of twelve minutes. The scheduled
workflow installs Ollama on the runner the same way, so CI exercises the learner's
path rather than a second one.

The `!override` example went with it. It used to live in the host-model overlay,
which turned off a service the base file's `depends_on` was waiting for; now the
base file has no such service. The sequence-concatenation trap it demonstrated is
still real and still worth knowing — the secure overlay's `ports` narrowing is the
surviving example.

What the bounded composer did not rescue, on the CPU lane, was everything after the
first few checks. Check 4 composed with a freshly loaded model and an idle machine and
made its budget reliably; by check 10 the same call was exceeding 60 seconds again,
because an abandoned generation does not stop when the client gives up — Ollama was
still burning 395% CPU on work nobody was waiting for, and each later call queued
behind that. A timeout is a promise to the caller, not a cancellation of the work.
The GPU hides this by finishing fast enough that the queue never builds, which makes
it worth stating rather than observing: it is still true on the host lane, and it is
what a saturated production deployment looks like. If you take one operational lesson
from this phase, that is a good candidate.

The **streaming** path is the sharper version of the same problem, and there it is
structural rather than contention. `tier.stream` is safe-buffered — the gate screens
the entire answer before releasing the first chunk — so a first-chunk deadline is
really a whole-generation deadline, on a generation the batch path has already paid
for once. Check 4 therefore holds the two paths to different standards, but only on
one lane: a batch fallback fails any run, and a stream fallback is allowed on `--ci`
alone, where it must still appear on `/health` naming the stream. "Allowed to degrade,
not allowed to be quiet about it" is the contract the service makes to its callers,
applied to its own verifier.

The lane restriction was missing for a while and is worth the sentence. The
concession's own comment described a hosted runner with four cores and a 1.7B, but no
guard scoped it there — so a full-fidelity release run could report 15/15 with
`/ask/stream` answered by the offline composer. A verifier that waives its own
substitution check on the lane that carries the release claim is measuring a tier
nobody ships, which is the failure the whole attestation exists to prevent. `--ci`
measures wiring and may miss a budget; a lane that reports a result may not.

### The tier assertion was eleven checks stale (2026-08-03)

Same substitution, one layer out. Checks 2 and 4 prove the tier and prove the model
composed; checks 5 through 15 then run, and two of them break the stack on purpose —
14 stops Qdrant, 15 restarts the assistant. The attestation was written after all of
them with no further reading of `/health`, so a composer that started falling back at
check 9 was recorded as `15/15` on the shipped tier, and every number in
`RELEASE-EVIDENCE.md` inherited that claim.

A complete run now ends with `final_tier_check`: one fresh batch question, then
`/health`, and the run dies unless the degradation map is empty and `brain`, `rag`,
`retrieval`, `embed` and `tier.stream` are still the real tiers. The question is not
decoration — the restart in check 15 rebuilds the service and clears the degradation
map, so an empty map on its own proves the map is new rather than that the model is
answering. The snapshot goes into the attestation as `final_tier`, and
`check-release-evidence.py` refuses a release whose attestation cannot produce it:
before this field existed the file simply could not answer the question, and "cannot
answer" is exactly the state that needed to become visible.

Lane consequence: a batch fallback already fails every lane, `--ci` included, so this
adds no new policy — it moves the existing one to the end of the run, where drift can
actually be seen. A partial run (`--from`, `--only`) skips the closing check for the
same reason it cannot attest: there is no complete run to re-assert.

### The buffered path had the cancellation flag and never read it (2026-08-03)

The 395% CPU above is the cost of an abandoned generation, and for the streaming path
the fix landed a round earlier: the outbound gate asks `deadline.check()` before it
pulls each chunk, so a client that leaves stops the source. Buffered `/ask` had the
same signal and no reader. `Budget.cancelled` did flip — the route is synchronous, so
it runs in the threadpool and the disconnect watcher keeps polling — but
`future.result(timeout=limit)` answers one question and cannot be asked another, and
`deadline.check()` only ran *between* retry attempts. A client that hung up two
seconds in was still charged sixty seconds of model.

Three seams, and any two without the third change nothing:

* the provider adapters became their own stream joined (`adapters.joined`), which
  checks the deadline between parts and, in a `finally`, **closes** the provider's
  iterator. Closing is the part that stops the work: an abandoned iterator leaves
  Ollama generating, which is how the measurement above happened;
* the wait polls in `POLL_SECONDS` slices and raises `Expired("caller disconnected")`
  when the flag flips. Clock exhaustion still raises `TimeoutError` with the message
  it always had, because 504 and 499 are different pages;
* `fallbacks.not_a_fallback` re-raises `Expired` instead of composing an offline
  answer. Without it the fix is worse than the bug: a hangup would be recorded as a
  degraded brain tier on `/health`, and the release lane's own no-fallback assertion
  would fail a run because somebody closed a tab.

Token counts survive the change because all three providers report them on the stream
— per-part for Ollama, a final usage frame for OpenAI, `get_final_message` for
Anthropic — so buffered cost is still the provider's number and not an estimate.

### And the streaming path was carrying the signal to a thread that could not see it (2026-08-04)

Both entries above end at the same place: the seam reads `deadline`, and `deadline`
lives in a `ContextVar`. `fallback_stream` drains the composer on a worker thread so it
can put a per-chunk timeout around a generator, and **a new thread starts with an empty
context**. `deadline.current()` in there returned a fresh unbounded `Budget` whose
`cancelled` is `lambda: False`, so on the only wiring the deployed service uses, every
one of those seams answered "nobody has left" for a caller who had. Measured over a
socket: 4 chunks delivered at disconnect, 41 and still climbing afterwards.

Nothing above was wrong, and that is the lesson worth keeping. The checks were right,
the exception types were right, the tests were green — and the signal never arrived,
because the fix and the code it protects ran in different contexts. `resilience.timed`
had already learned this once, from the opposite direction: token counts written by an
adapter into a worker's context died with the thread, and the release page reported
estimates while exact numbers sat unread. Same hole, same `copy_context()`, three
months apart.

The drain now runs inside a copied context (the copy shares the `Budget` **object**, so
the flag the watcher flips is the flag the worker reads), checks the deadline between
frames, and closes the source in a `finally`. It also stops when the response generator
ends for any other reason — a truncation, a gate that ended the response, a consumer
that simply stopped — because a budget cannot see "nobody is reading the queue".

The test that would have caught it did not exist: `tests/test_disconnect.py` assigned
`stream_compose` directly, which is the one composition production never uses. It now
covers both wirings.

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
