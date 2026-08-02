# Incident-response runbook — the capstone assistant

Short, actionable, and tied to the signals this stack actually emits. Each
scenario follows the same shape: **detect → contain → diagnose → recover →
learn**. The observability primitives referenced here are `/health`
(`status`, `degraded`, `spans_recorded`), the SQLite audit log, and the
OpenTelemetry spans (in-memory always; OTLP when `OTEL_EXPORTER_OTLP_ENDPOINT`
is set).

## 1. A prompt injection landed (or a red-team case regressed)

- **Detect**: `make redteam` fails in CI; or the audit log shows a `tool.ran`
  entry you cannot match to a legitimate `approval.granted` for that subject.
- **Contain**: revoke standing grants by restarting the service (grants are
  in-process by design); if auth is on, rotate `ASSISTANT_JWT_SECRET` to
  invalidate all outstanding tokens.
- **Diagnose**: pull the failing input from the red-team report; check which
  layer should have caught it — L1 screen (`guardrails.py`), context screen
  (`screen_contexts`), tool-output hardening (`harden_registry`), or the
  approval gate.
- **Recover**: add the payload as a NEW row in
  `phase6-design-defend/01-red-team/*/evals/redteam.jsonl` (bump nothing —
  the version field changes only on schema changes), then fix the layer until
  `make redteam` is green again.
- **Learn**: if the payload is a new *family*, add a category, not just a row.

## 2. `/health` reports `degraded`

- **Detect**: `status: "degraded"` with a `degraded` map naming the component
  (`rag`, `brain`, `tools`) and the reason.
- **Contain**: nothing to contain — degraded mode IS the containment. Answers
  continue from the offline tier; ingest mirrors into the warm standby.
- **Diagnose**: `docker compose ps` + the named component. `rag` → Qdrant
  container or network; `brain` → Ollama (check its healthcheck: are the models
  still present?); `tools` → the MCP container never answered discovery.
- **Recover**: `docker compose restart <service>`. The assistant re-runs
  discovery only at boot, so after MCP recovers, `docker compose restart
  assistant`. Confirm `/health` returns to `ok`.
- **Learn**: if the same component degrades repeatedly, check its memory limit
  in `docker-compose.yml` — OOM-killed containers look like flaky networks.

## 3. PII appeared where it should not

- **Detect**: a `[redacted: output failed the safety gate]` answer (the gate
  fired — working as intended), or worse, a report of PII in a real response.
- **Contain**: if auth is on, identify the caller from the audit log; if the
  leak came through a corpus document, delete the collection
  (`assistant_data` volume / Qdrant collection) — the corpus is rebuildable
  by re-ingesting.
- **Diagnose**: PII reaches an answer only if it survived BOTH the document
  screen (redaction on ingest-time retrieval) and the output gate. Reproduce
  with the offending document offline; check the `PII` patterns in
  `guardrails.py` for the format that slipped (new phone format? IBAN?).
- **Recover**: extend the `PII` patterns; add the format to the phase6 `pii`
  rows; re-run `make redteam` and the capstone fast suite.
- **Learn**: PII patterns rot. Schedule a review whenever a new data source
  (connector, corpus) is added.

## 4. Latency spiked / requests being shed

- **Detect**: callers see 429/503; or P99 over the span durations grows (the
  deployed-stack drill in `WORKSHOP-DEPLOYED-STACK.md` shows how to read it).
- **Contain**: 429/503 IS load shedding working; raise `RATE_LIMIT_RPS` /
  `MAX_CONCURRENCY` only if the downstream can take it.
- **Diagnose**: find the slow span. `tool:*` spans point at a connector or the
  MCP hop; a slow `agent.run` with fast children points at composition —
  check Ollama (model swapped? host under memory pressure?).
- **Recover**: for a slow tool, the per-call timeout in `resilience.py` already
  bounds the damage; fix or replace the connector. For Ollama, confirm the
  model tag matches what the compose bootstrap pulled.
- **Learn**: record the incident's span tree; it becomes the fixture for the
  next trace-diagnosis drill.

## 5. A retried approval double-fired (should be impossible — treat as a bug)

- **Detect**: audit log shows two `tool.ran` rows for one `approval.granted`
  (no second grant, no `approval.replayed` in between).
- **Contain**: restart the service (clears in-process grants).
- **Diagnose**: check the client sent an `Idempotency-Key`; without one, two
  POSTs are two legitimate approvals by contract. With one, inspect the
  `idempotency_keys` table in the `ASSISTANT_DB` file.
- **Recover / learn**: if the client cannot send keys, add server-side
  fingerprinting (subject + tool + time window) — and add the failing sequence
  to `test_reliability.py` first.

## State: backup and restore

All durable state — memory, audit log, idempotency keys — lives in ONE SQLite
file (`ASSISTANT_DB`, the `assistant-data` compose volume; ADR-0005), so backup
is a file copy taken through SQLite's own online-backup so a mid-write copy can
never be torn:

```bash
docker compose exec assistant python -c \
  "import sqlite3; sqlite3.connect('/data/assistant.db').backup(sqlite3.connect('/data/backup.db'))"
docker compose cp assistant:/data/backup.db ./assistant-backup.db
```

Restore is the reverse (`docker compose cp` the file back to `/data/assistant.db`
while the service is stopped, then `docker compose start assistant`). Verify a
restore the same way e2e verifies persistence: memory recalls across the restart
and `sqlite3 assistant.db 'select count(*) from audit_log'` matches the backup.
Qdrant's collection rebuilds from re-ingestion; Ollama's models re-pull — the
SQLite file is the only state you cannot regenerate, which is why it is the only
thing this procedure covers.

## Escalation

This is a single-operator local stack: "escalation" means filing an issue with
the audit-log excerpt, the `/health` payload, and the span tree attached. All
three exist precisely so that the report is reconstructable after the fact.
