# Threat model — the capstone assistant

STRIDE-lite over the components that actually exist in this repo. Every
mitigation cell names the code that implements it and the test that proves it;
nothing here is aspirational.

## System at a glance

```
caller ──HTTP──► FastAPI service (api.py, wired by service.py)
                   │  auth.py (optional JWT)         [trust boundary 1: caller]
                   │  guardrails.screen on input
                   ├──► agent loop (agent.py)
                   │      ├─ tools.py / connectors.py [trust boundary 2: tool output]
                   │      └─ MCP server (mcp_server.py, network in compose)
                   ├──► RAG (InMemoryRag | Qdrant)    [trust boundary 3: corpus]
                   ├──► memory (in-process | SQLite)
                   └──► composer (offline | Ollama)
```

Untrusted inputs cross three boundaries: what the caller types, what a tool
fetches, and what retrieval returns. All three are screened; none can approve
anything.

## STRIDE, per element

| Threat | Where it lands | Mitigation (code) | Proof (test) |
|---|---|---|---|
| **S**poofing — caller pretends to be someone else | HTTP surface | `ASSISTANT_JWT_SECRET` turns on Bearer-JWT validation: signature, expiry, audience, scope (`auth.py`) | `test_auth.py` (forged/expired/wrong-audience/wrong-scope all 401) |
| Spoofing — token minted for another service replayed here | HTTP surface | audience check (RFC 8707 resource binding) | `test_a_token_for_another_audience_is_rejected` |
| **T**ampering — prompt injection in the user message | guardrails L1 | `guardrails.screen`: decode-then-scan, multilingual + exfiltration patterns | `test_an_injected_question_is_refused_at_the_door`; phase6 red-team v2 |
| Tampering — indirect injection via a poisoned document | RAG corpus | every retrieved doc re-screened before it becomes evidence; injection-bearing docs dropped (`screen_contexts`), evidence spotlighted in the model prompt | `test_the_service_never_composes_from_a_poisoned_context` |
| Tampering — injection via tool/MCP output | tool boundary | `harden_registry` re-screens every read-only tool's output, MCP tools included | `test_poisoned_tool_output_is_screened_before_the_agent_sees_it` |
| Tampering — content claims "already approved" | agent loop | approval lives only in server-side grant records, never in content; each grant pays for ONE run | `test_an_approval_authorizes_exactly_one_run`; phase6 `approval-bypass` rows |
| Tampering — approved call is swapped for another | agent loop | the grant carries a fingerprint of the canonical arguments, checked at execution | `test_approving_a_tool_without_its_arguments_authorizes_nothing` |
| **R**epudiation — "who approved that send?" | whole service | persistent SQLite audit log: policy decisions, tool runs, approvals, each with the verified subject | `test_the_audit_log_records_the_whole_approval_story_with_identities`, `test_the_audit_trail_survives_a_process_restart` |
| **I**nformation disclosure — PII leaks in answers | output gate | `guardrails.output_ok` on every composed answer (batch and streamed) | `test_pii_never_passes_through_untouched` (phase6), stream redaction path in `test_stream.py` |
| Information disclosure — cross-tenant reads | RAG + memory | tenant = verified JWT `sub`: per-tenant BM25 index offline, server-side Qdrant payload filter in production; memory rows namespaced `user:<sub>` | `test_one_tenant_cannot_retrieve_another_tenants_documents`, `test_qdrant_tenant_filter_isolates_users` (integration) |
| Information disclosure — data exfiltration requests | guardrails L1 | transfer-verb + external-destination patterns block outright | phase6 `exfiltration` rows |
| **D**enial of service — request floods | HTTP surface | token-bucket rate limit (429) + concurrency cap (503), `/health` exempt | `test_requests_beyond_the_burst_get_429`, `..._cap_get_503` |
| DoS — a hung adapter takes the service down | adapters | per-call timeouts + retries (`resilience.py`), then fallback to the offline tier with `/health` reporting `degraded` | `test_a_dead_rag_backend_degrades_to_the_offline_tier` |
| DoS — one runaway container starves the host | compose | pinned images, memory/cpu limits, `restart: unless-stopped`, `stop_grace_period` | compose structural checks in `phase8-deploy/01-compose` |
| **E**levation of privilege — agent fires an irreversible tool | agent loop | HITL: `requires_approval` tools pause; approval is a single-use grant bound to subject + arguments + expiry, claimed atomically at the call site; replayed `/approve` (idempotency key) is a no-op | `test_a_gated_tool_pauses_until_it_is_approved`, `test_a_replayed_approval_does_not_grant_twice` |
| Elevation — one caller spends another caller's approval | agent loop | the grant names the verified subject; a different subject finds no grant | `test_one_subjects_approval_cannot_authorize_another_subjects_send` |
| Elevation — two concurrent requests spend one approval | agent loop | consume is a single `DELETE ... RETURNING`; exactly one caller wins the row | `test_one_grant_survives_a_stampede_of_concurrent_consumers` |
| Elevation — token with the wrong scope calls a privileged route | HTTP surface | per-endpoint scopes (`assistant:ask/ingest/approve`) | `test_a_token_missing_the_endpoint_scope_is_rejected` |

## What this model does NOT cover (accepted, documented)

- **Secrets management**: `ASSISTANT_JWT_SECRET` / `TELEGRAM_BOT_TOKEN` arrive as
  env vars. A real deployment moves them to a secret store; out of scope for a
  local-first course stack.
- **Transport encryption**: compose runs plain HTTP on an internal network with
  one published port. TLS termination belongs to whatever fronts the service.
- **Model-level attacks** (weight extraction, adversarial suffixes against the
  local model): the containment stance assumes injections WILL land and bounds
  the blast radius instead.
- **Availability of the host itself**: single-machine compose; no HA story.

See `RUNBOOK.md` for what to do when one of the mitigated threats fires anyway.
