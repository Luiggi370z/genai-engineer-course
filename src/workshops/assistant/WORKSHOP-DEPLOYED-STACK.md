# Workshop · Deployed stack  (ends Phase 8)

The assistant works, it is hardened, and it speaks MCP. It is also a black box that
costs an amount nobody has measured and takes a length of time nobody has bounded.
This layer closes that: **see it, then make it cheaper without making it worse.**

Two modules, in this order, because the second one is only safe once the first exists.

## Architecture

```
                          ┌── traced_registry(REGISTRY) ── every tool wrapped
                          │      tool.name · tool.requires_approval
goal ──► traced_run(run) ─┤      no tool edited, none can forget
     agent.run root span  │
       steps · paused     └── spans ──► time_by_tool · slowest_tool
                                        gated_tool_calls  (safety report)
                                              │
                                              ▼
goal ──► cached_run(goal, run, cache) ──► AnswerCache
              look · run · OFFER              refuses: paused runs,
                                              side-effecting runs, step-cap
                                              runs, empty answers
```

## The seam

`before/src/assistant/observe.py` — `traced_tool` / `traced_registry`, `traced_run`,
and the readers (`tool_calls`, `time_by_tool`, `slowest_tool`, `failed_spans`,
`gated_tool_calls`). The provider wiring and the attribute names are given.

`before/src/assistant/cache.py` — `answer_key`, `is_cacheable`, `AnswerCache.get` /
`offer`, and `cached_run`.

## Why the tools are wrapped, not edited

Tracing is a cross-cutting concern, and cross-cutting concerns rot when they live
inside every implementation: somebody adds a tool, forgets the decorator, and six
weeks later there is a hole in the trace nobody can explain. `traced_registry` makes
instrumentation a property of the **seam**, so a new tool is traced whether its author
thought about it or not.

## Why caching an agent is not caching RAG

A RAG answer is a pure function of a question and a corpus. An agent run sends
messages and books meetings. If you cache "text my boss the summary", the second
request returns instantly — and no message is sent. Nothing errors. Nobody is paged.
The user finds out from their boss.

That is why `offer` exists instead of `put`: the caller proposes an answer and the
policy decides, reading the **trace** to see which gated tools actually fired. The
observability module isn't just a dashboard feed; it is the input to a safety
decision.

## Deliverables

- [ ] Every tool is traced by **wrapping the registry** — a test proves a newly-added
      tool is instrumented without its author doing anything
- [ ] A failing tool is marked **ERROR on its span and still raises** — the trace
      records the failure, it does not absorb it
- [ ] The root `agent.run` span carries **step count and whether it paused**, so a
      run that stopped for a human is distinguishable from one that hit the cap
- [ ] The same root span tells the **approval story**: which grants the run started
      with (`agent.approved_tools`), which tool a paused run waits on
      (`agent.pending_tool`), and a single `agent.outcome` — `completed`,
      `paused_for_approval` or `policy_violation` (the last one is span-status
      ERROR, because it is the trace a reviewer must never scroll past)
- [ ] `gated_tool_calls` reports **which irreversible tools actually fired**, and a
      test proves a contained run reports none
- [ ] `time_by_tool` / `slowest_tool` answer **where the wall clock went**, read off
      the spans rather than from a timer you sprinkled around
- [ ] The cache **refuses** a paused run, a side-effecting run, a step-cap run and an
      empty answer — one test per rule, because each is a different way to break trust
- [ ] A repeated read-only question **does not rerun the agent**; a side-effecting one
      reruns **every time**, and a test asserts both
- [ ] The whole layer runs offline: `InMemorySpanExporter` in tests, no collector, no
      vendor account

## The operate drill: diagnose from the trace, not the code

Production failures do not announce which tool broke. `tests/test_diagnosis.py`
seeds the two classic incidents — one tool quietly degraded, one intermittently
failing — and diagnoses them **from the spans alone**:

1. **Symptom** — the `agent.run` root span got slow (`duration_ms`).
2. **Localise** — `time_by_tool` / `slowest_tool` name the culprit; no code read.
3. **Confirm** — `failed_spans` separates *broken* (retry/fix upstream) from
   *slow* (capacity/caching) on the same trace, because the two need different
   fixes.

The drill also shows why the CI gate budgets **P99, not the mean**: one degraded
call in ten barely moves the average and owns the tail. Rehearse it offline, then
run the same three readers against the collector copy of the spans in the deployed
stack — that is the "diagnose" step of `RUNBOOK.md`, practised before the pager
goes off.

## The capstone: one running service

Everything above still treats the assistant as a library. The capstone makes it a
service, organized so each module owns exactly one concern — `service.py` is the
**composition root** (the one file where adapters are chosen), `api.py` is the
HTTP surface, `core.py` is the request pipeline, `composers.py` turns evidence
into prose, `screening.py` guards the trust boundaries, and `fallbacks.py` keeps
a dead adapter from becoming a dead service. Together they wire every layer you
built:

```
request ─► guardrails.screen ─► agent.run (traced) ─► tools (read-only output
           (input)                │                    re-screened; irreversible
                                  │                    ones gated by /approve)
                                  ├─► RAG   (in-memory BM25  | Qdrant)
                                  ├─► memory (in-process     | SQLite)
                                  └─► spans  (in-memory      | + OTLP)
           guardrails.output_ok ◄─ answer
```

Offline and deterministic by default — the fast tests drive the real FastAPI app
with a TestClient and no network. Each real adapter turns on with one env var
(`settings.py`): `QDRANT_URL`, `OLLAMA_HOST`, `MCP_SERVER`, `ASSISTANT_DB`,
`OTEL_EXPORTER_OTLP_ENDPOINT`, plus three optional hardening/connector vars —
`ASSISTANT_JWT_SECRET` (Bearer JWT on every mutating endpoint, `auth.py`),
`TELEGRAM_BOT_TOKEN` and `NEWS_FEED_URL` (real connector bodies, `connectors.py`;
the approval gate and output re-screen apply unchanged). `adapters.py` holds the
real implementations, `sqlite_memory.py` is the memory store that survives a
restart, and `mcp_server.py` is a small real MCP server the assistant discovers
tools from.

The HTTP surface is `/health`, `/ingest`, `/ask`, `/ask/stream` (the same answer
as server-sent events, chunk by chunk), and `/approve`. Grounded answers carry
structured `citations` (`[{id, source, snippet}]`) that the model-tier prompt
labels with the same `[c#]` ids.

The `Dockerfile` builds one image that runs as both the assistant API and the MCP
server; `phase8-deploy/01-compose` deploys it next to pinned Qdrant and Ollama, and
`src/verify-e2e.sh` proves the composed stack end to end: boot on healthchecks,
tier report, grounded answer, approval containment, an MCP call over the wire,
spans left behind — and, via the `docker-compose.observability.yml` overlay, the
same spans arriving at a real otel-collector **outside the process**.

### Capstone deliverables

- [ ] `service.py` + `core.py` compose **every** layer — guardrails on input,
      hardened tool output, gated tools behind `/approve`, RAG contexts, memory
      writes, spans — and the fast tests prove each seam offline
- [ ] `/ask/stream` streams the same gated pipeline as SSE, grounded answers carry
      structured citations, and the optional JWT gate rejects missing/expired/
      wrong-audience/wrong-scope tokens (all proven offline in `tests/`)
- [ ] Security depth holds offline: poisoned retrieved documents are dropped
      before composition, tenants cannot cross-read documents or memories, every
      approval and tool run lands in the persistent audit log, and a replayed
      approval never fires twice (`tests/test_security.py`,
      `tests/test_reliability.py`; threat model in `THREAT-MODEL.md`, incident
      response in `RUNBOOK.md`)
- [ ] Memory survives a **process restart** (`sqlite_memory.py`; the tests reopen
      the store cold)
- [ ] MCP tools arrive by **discovery through the real SDK** (`adapters.mcp_tools`
      against `mcp_server.py`, in-memory in the integration lane, over HTTP in the
      composed stack)
- [ ] `docker compose up --build` in `phase8-deploy/01-compose/after` reaches
      healthy, and `./verify-e2e.sh` passes all eleven checks — including the
      operate tier: spans observed at a real collector outside the process,
      degraded-but-honest answers with Qdrant stopped, and state that survives a
      restart (grounded answers, audit rows, memories)
- [ ] `make report` writes `PORTFOLIO.md` — eval scores per slice, live red-team
      containment, latency percentiles read off the spans, the cost story and the
      ADR list, every number measured by `src/assistant/report.py` and the
      generator itself tested (a breach cannot pass silently)
- [ ] The design is documented like a system, not a homework: diagrams in
      `ARCHITECTURE.md`, decisions with alternatives and costs in `adr/`, threats
      in `THREAT-MODEL.md`, incidents and backup/restore in `RUNBOOK.md`

## Stretch goals

- Ship the spans to a real backend. The observability overlay already proves they
  leave the process; swap its debug exporter for an `otlp` exporter at a local
  Phoenix or a Langfuse project and look at the actual tree. Change **nothing** in
  `observe.py` — if you have to, your instrumentation is not portable yet.
- Put cost on the spans. Bring the Phase-1 meter in, set `cost.usd` per model call,
  and report spend per goal. Then find the single most expensive request you have ever
  made and explain, from the trace alone, why it cost that.
- Add a **semantic** layer to the cache (`phase8-deploy/04-cost-latency`) and sweep the
  threshold on your own traffic. Report the wrong-reuse count, not just the hit rate.
- Gate the deploy on the tail: fail CI when P99 across your golden set exceeds the
  budget, using the guard from `03-deploy-observe`.

Implement `observe.py` and `cache.py`. Reference and tests:
`after/src/assistant/observe.py`, `after/src/assistant/cache.py`,
`after/tests/test_observe.py`, `after/tests/test_cache.py`.

**Measure before you optimize, and report the pair.** A cache that halves your bill and
loses two points on the Phase-3 gate is not a win, it is an undeclared quality cut. The
order — see it, then cache it, then route it — exists so that when the score moves you
know exactly which rung to blame.
