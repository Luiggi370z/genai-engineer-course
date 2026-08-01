# Phase 4 · System-design mock worksheet (45 minutes, timed, out loud)

> "Design a RAG system over 10M enterprise docs, p95 < 2s, multi-tenant,
> handling untrusted documents."

Record yourself. Score against the 8 steps afterward — anything you didn't say
out loud doesn't count.

## The 8-step script
1. **Clarify (4+ questions):** QPS? p95 target? freshness? tenancy model? PII /
   data residency (does it force self-hosted models)? threat model?
2. **Split the system:** ingestion (batch, on doc change) vs serving (per request).
3. **Retrieval:** hybrid + rerank; tenant isolation via namespaces / metadata filters.
4. **Evaluation:** golden set + RAGAS gating every change in CI.
5. **Observability:** tracing + cost per query.
6. **Cost levers, in order:** cache -> route (local->cheap->frontier) -> compress.
7. **Failure modes + named mitigations:** injection, hallucination, loops, rate
   limits, PII, cost runaways.
8. **Security as an implemented layer:** guardrails on BOTH pipelines, least
   privilege, HITL, abstain path.

## Self-scoring rubric (1 pt each, 10 total)
- [ ] Asked 4+ clarifying questions before drawing
- [ ] Drew the ingestion/serving split explicitly
- [ ] Hybrid + rerank named, with tenant isolation
- [ ] Evaluation in CI (not just "we'd test it")
- [ ] Observability: cost + latency per query
- [ ] Cost levers in the right order (cache first)
- [ ] Named 3+ failure modes with specific mitigations
- [ ] Guardrails on the INGESTION side (indirect injection) — the commonly-missed one
- [ ] Abstain path with a groundedness gate
- [ ] Mentioned the on-prem/regulated variant as a config change

8+/10 = strong senior signal. Below 6 = re-run tomorrow.
