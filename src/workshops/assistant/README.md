# Workshops · the evolving assistant

Workshops 2 through 8 build **one** personal assistant that grows across the course.
The two bookends live elsewhere: Workshop 1, the model bench, in `../model-bench/`,
and Workshop 9, the interview loop, in `../interview-loop/` (markdown only — the
artifact is a habit, not a repo).
`before/` is your scaffold (TODOs); `after/` is the working reference.

| Workshop | Ends phase | Adds | Files | Brief |
|----------|-----------|------|-------|-------|
| RAG service | 2 | hybrid-retrieval core over chunks that know their source, revision and character span | `rag.py` | `WORKSHOP-RAG-SERVICE.md` |
| Eval suite + CI gate | 3 | golden set, injectable judge, calibration, gate | `evals.py` | `WORKSHOP-EVAL-SUITE.md` |
| Personal assistant | 4 | agent loop, tools, HITL | `tools.py`, `agent.py` | `WORKSHOP-ASSISTANT.md` |
| Memory + research crew | 5 | memory with TTL + provenance, one store per subject, budgeted context, tiered delegation | `memory.py`, `tenancy.py`, `crew.py` | `WORKSHOP-MEMORY-CREW.md` |
| Hardened assistant | 6 | guardrails that expand and squash before they scan, spotlighting, output gate, an optional model in the loop | `guardrails.py`, `guard.py` | `WORKSHOP-HARDENED.md` |
| Your own MCP | 7 | consume an MCP server by discovery, and a planner that can actually choose what was discovered | `mcp_client.py`, `planner.py` | `WORKSHOP-MCP.md` |
| Deployed stack | 8 | one OTel trace per request — a root and a child per stage, tools wrapped at the seam, model/prompt/corpus stamps derived rather than typed, tokens and cost on the compose span — a corpus that can be updated, deleted and cited back to its text, one time budget every layer shares, effects that survive a retry, and an answer cache with refusal rules | `observe.py`, `provenance.py`, `usage.py`, `rag.py`, `adapters.py`, `deadline.py`, `resilience.py`, `idempotency.py`, `outbox.py`, `cache.py` | `WORKSHOP-DEPLOYED-STACK.md` |
| Capstone: the composed service | 8 | One module per concern: composition root, HTTP surface, request pipeline, composers, trust-boundary screening at ingest and retrieval, degraded fallbacks; real adapters (Qdrant + real embeddings, Ollama, MCP SDK, OTLP) behind env vars; a corpus keyed by derived chunk ids so re-ingest updates and citations resolve; one deadline per request that every layer's timeout fits inside, idempotency on every mutation and an outbox that records irreversible intent before it happens; SQLite memory; a JWT gate with a pluggable issuer and the OAuth 2.1 + PKCE flow that feeds it; an MCP server; a Docker image; one traced request end to end | `service.py`, `api.py`, `core.py`, `planner.py`, `composers.py`, `screening.py`, `guard.py`, `fallbacks.py`, `settings.py`, `rag.py`, `adapters.py`, `deadline.py`, `resilience.py`, `idempotency.py`, `outbox.py`, `connectors.py`, `sqlite_memory.py`, `tenancy.py`, `auth.py`, `oauth.py`, `provenance.py`, `usage.py`, `mcp_server.py` | `WORKSHOP-DEPLOYED-STACK.md` |

Do them in order — each builds on the last, and from the eval layer onwards every
later layer is measured by the one before it. Then finish with the **defect lab**
(`WORKSHOP-DEFECT-LAB.md`, `make defect-lab`): three vulnerabilities this code
actually shipped, kept as running variants, and the regression tests you write to
catch them — proved by going red on each seeded defect before going green.

```bash
cd after && make check     # the reference passes; your job is to make before/ pass
```

The capstone runs offline and deterministic by default (that is what `make test`
exercises); each real adapter turns on via one env var (`QDRANT_URL`,
`OLLAMA_HOST`, `MCP_SERVER`, `ASSISTANT_DB`, `OTEL_EXPORTER_OTLP_ENDPOINT`). The
`Dockerfile` here builds the image that `phase8-deploy/01-compose` deploys, and
`src/verify-e2e.sh` (repo root of the companion code) proves the whole composed
stack boots, retrieves, contains, and traces.

## A teaching reference, not a production authority

Read this before you copy anything out of `after/`.

This code is written to be *understood* — every trade-off is argued in a
docstring, every unsafe alternative is kept beside the safe one so you can see
the difference, and the whole thing runs offline on a laptop. Production code is
written to be *operated*, and the two goals disagree constantly. Here the
defaults are chosen so a learner can run them; there they would be chosen so an
on-call engineer can survive them.

Three concrete places the difference bites. The SQLite file that backs memory,
audit, approvals and the outbox is one process's file, and the atomic
`DELETE ... RETURNING` that makes approvals safe is a SQLite guarantee, not a
distributed one — the moment you run two replicas you need a real database and
a fresh argument about the same properties. `ASSISTANT_STREAM_MODE=raw` exists
and is unsafe on purpose, because seeing the vulnerable path next to the fixed
one is the lesson; nothing stops an operator setting it. And the offline
composer, stub connectors and in-memory tracer that make `make check` hermetic
are exactly the components you must replace before any of this is real.

The strongest evidence that this is a teaching artifact is `after/defects/`:
three vulnerabilities that were in this code, reviewed and green, until an audit
found them. They are kept as running code. `make defect-lab` runs your
regression tests against the fix (must pass) and against each defect seeded back
in (must fail) — see [`WORKSHOP-DEFECT-LAB.md`](WORKSHOP-DEFECT-LAB.md). A
codebase that ships its own vulnerabilities as coursework is not claiming to be
an authority; it is showing you what review actually catches, and when.

The system documentation lives beside the code: [`ARCHITECTURE.md`](ARCHITECTURE.md)
(component + data-flow diagrams), [`adr/`](adr/) (thirteen decision records),
[`THREAT-MODEL.md`](THREAT-MODEL.md), [`RUNBOOK.md`](RUNBOOK.md). `make report`
in `after/` runs the service on trial and writes the result twice: `PORTFOLIO.md`
— the measured one-page summary (evals, red-team, latency, cost, decisions) a
reviewer reads first — and `evals/report.json`, the version-stamped record the
merge gate reads. `make gate` runs that gate locally; CI runs it against the
image built from the current commit.

## `make release-evidence` — the same trial, on the system that ships

`make report` is a proxy and says so in its own header: in-memory retrieval, a
lexical judge, three containment probes, one second. That is the right trade for
something that runs on every push, and the wrong number to publish.

`make release-evidence` runs the same harness against the deployed stack —
Qdrant with the semantic embedder, hybrid retrieval, reranking **on**, a RAGAS
0.4 judge on a pinned model, and all 58 rows of the versioned Phase 6 red-team
dataset including its eleven benign controls. It needs the compose stack up, and
it **refuses to run** if any component has fallen back: a release number produced
against the offline path is not a weaker measurement, it is a different one under
the same heading.

The controls are the half worth arguing about. Containment is trivially
satisfiable — refuse everything and no attack ever reaches a tool — so the report
prints two numbers side by side and never one: attacks that reached a gated tool,
and benign requests that were wrongly refused. A guardrail change that improves
the first by wrecking the second is visible in one glance instead of shipping as
a win.

`docs/RELEASE-CHECKLIST.md` makes a stamped run of this a precondition for
publishing, and carries the table of which lane may claim what.

## `make evidence` — the log for the whole course

`make report` measures this service. `make evidence` measures **the course**,
across the six dimensions a reviewer asks about — quality, latency, cost,
security, failure recovery, and the decisions behind them — into `EVIDENCE.md`
and `evidence/manifest.json`. The capstone's own numbers come from the same pass
as `PORTFOLIO.md`, so the two pages cannot end up describing different systems.
Everything earlier reads a small JSON file that its phase left behind.

The design decision worth understanding before you run it: **the default for
every claim is unproven, and unproven rows are printed, not skipped.** That is
the difference between a manifest and a checklist. A checklist records what you
say you did, so it reports the same thing for work finished and work skipped —
and therefore tells you nothing about either. This records what left a file
behind, and prints the one command that would close each gap.

The consequence, so you do not think it is broken: **your first run is almost
entirely red.** You have not generated the artifacts yet. A page that went green
on day one would have nothing left to tell you on day ninety.

`Decisions` is the one section with no score, deliberately. An ADR is an argument
and arguments are judged by reading them; counting them would make the single
qualitative dimension gradeable by writing more files, which is exactly the
self-attestation the other five refuse.
