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

## Stretch goals

- Ship the spans somewhere real. Set `OTEL_EXPORTER_OTLP_ENDPOINT` at a local Phoenix
  or a Langfuse project and look at the actual tree. Change **nothing** in
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
