# Verification stamp — `workshops`

**Last verified:** 2026-08-02
**How:** every `after/` reference passed `make check` (ruff + pyright + pytest) on this date,
and every `before/` scaffold passed lint + type with its tests failing by design.

**What this stamp pins — and what it does not.** Ranges, not versions. Every lesson's
`pyproject.toml` declares upper-bounded *ranges* (`ragas>=0.4,<0.5`), so a fresh
`uv sync` resolves the newest release inside the range, which is usually — not
necessarily — what the date above was taken against. Where this file names an exact
version, that is a **record** of what the verified run resolved to, not a constraint
that reinstalls it. Exactly one lockfile is tracked in the whole repo,
`workshops/assistant/after/uv.lock`: the capstone is the only bit-reproducible thing
here, because it is the only thing that gets deployed. Everything else is
version-bounded. Interpreter: **3.11 through 3.14** (`>=3.11,<3.15`), with both ends
run in CI on every push; `phase4-agents/04-framework-bakeoff` pins 3.12 and says so
itself. The long version is in [`../README.md`](../README.md).

## What landed on 2026-07-31

`model-bench/` is new (**W1**) and is the only workshop that talks to a vendor SDK
directly, so `openai` sits in an `integration` dependency group rather than the main
`dependencies`. That means `providers.py` cannot be resolved by the fast tier, which is
why `reportMissingImports = "none"` is set for pyright there — an unusual setting, and
deliberate: the alternative is making every student install a hosted SDK to run offline
tests.

`assistant/` gained the **W8** layer, which pins `opentelemetry-sdk`. The tests read
spans back through `InMemorySpanExporter`, so the instrumentation is verified with no
collector and no network. If an OTel minor bump breaks anything, it will surface here
first as an attribute-name change rather than an import error.

`assistant/` also gained the **capstone service**: `service.py` (FastAPI composition
root, tested with `TestClient` offline), `sqlite_memory.py`, `settings.py`,
`adapters.py`, `mcp_server.py`, and a `Dockerfile`. The real adapters live in an
`integration` dependency group — `qdrant-client`, `ollama`, `mcp>=2.0.0,<3` (the v2
SDK; v1 code will NOT run on it), `opentelemetry-exporter-otlp` — imported lazily so
the fast tier never installs them. The MCP adapter and server are verified against
the REAL v2 SDK via its in-memory client (`pytest -m integration`: 2 pass with the
group installed, the Qdrant/Ollama/boot lanes skip without their endpoints).

## What landed on 2026-08-01

The capstone grew its production tier: `auth.py` (opt-in Bearer JWT, `pyjwt>=2.8,<3`
in the main dependencies — pure-Python, no key infrastructure), `connectors.py`
(real Telegram/RSS tool bodies behind env vars), `resilience.py` + `idempotency.py`
(retries/timeouts, token-bucket + concurrency-cap middleware, replay-safe
approvals), `audit_log.py` (persistent, same SQLite file as memory), streaming
(`/ask/stream`), structured citations, tenant scoping, and `report.py`
(`make report` → `PORTFOLIO.md`). Three field bugs worth remembering, all caught by
the live 11-check e2e run against real Ollama (a thinking model that spends minutes
reasoning before its first token):

1. The timeout in `resilience.py` originally used `ThreadPoolExecutor` as a context
   manager, whose exit blocks on the abandoned worker — the timeout raised on
   schedule and then waited anyway. Pinned by
   `test_a_timeout_returns_promptly_instead_of_waiting_for_the_abandoned_call`.
2. `fallback_stream` guarded errors but not TIME — a generator's slowness happens
   between yields, where `resilient` cannot see it, so `/ask/stream` hung for the
   whole generation. Now each chunk must arrive within the compose deadline or the
   stream falls back/truncates. Pinned by the stall tests in `test_reliability.py`.
3. `offline_compose`, running as the degraded fallback for the model tier, answered
   with whatever Qdrant retrieved — but a vector store returns the nearest
   neighbours of ANY question, so "nearest" was quietly treated as "relevant".
   The fix was a content-word filter in the composer, and **it was the wrong layer**;
   see 2026-08-02 below for what replaced it. The diagnosis was right and stands:
   vector search never abstains.

The capstone's `service.py` had grown to ~650 lines carrying six concerns, so it
was split along its natural seams — `service.py` (composition root only),
`api.py` (HTTP surface; the uvicorn factory moved with it, see the Dockerfile
CMD), `core.py` (the Assistant pipeline), `composers.py`, `screening.py`, and
`fallbacks.py` — every module now sits inside the 150–500-line band the course
preaches. Same tests, same behavior; only import paths moved.

## What landed on 2026-08-02

Two capstone defects, both found by audit rather than by the suite, and both worth
more as lessons about *where* a rule belongs than as fixes.

1. **The relevance filter was in the composer.** The content-word filter added on
   2026-08-01 (item 3 above) sat downstream of a semantic retriever and discarded
   synonym-only hits — the exact result the embedder exists to produce. "How quickly do
   i get money back for a work trip" retrieved the travel-expenses page at 0.66 cosine
   and the assistant answered "I don't know" with the page sitting in `contexts`. A
   filter can only use what its layer can see, and all a composer can see is text.
   Relevance now lives at the store: `ASSISTANT_MIN_SCORE=0.58` in the deployed
   compose file (measured — synonym true positive 0.6596, best off-topic neighbour
   0.5097), `Chunk.score`/`Chunk.scored_by` ride into the citation, a Qdrant store with
   no floor reports `relevance` in `degraded`, and `require_real_tiers` will not publish
   release recall measured without one. `test_the_degraded_composer_does_not_fabricate_grounding`
   was asserting the wrong behaviour and is now
   `test_the_degraded_composer_answers_from_whatever_retrieval_kept`; the tenancy fakes
   score their neighbours and apply a floor, so abstention is exercised where it now
   happens.
2. **The stream gate's bound was about matches, not candidates.** Third time on this
   property. `HOLDBACK_CHARS` bounds the longest span a pattern can *match*, so an
   over-long email address matches on its last 64 characters and the hundreds in front
   belong to no match at all — measured: 108 characters of a 500-char local part
   released before blocking, 608 of a 1000-char one. The gate now takes the tighter of
   that span bound and a **token** bound (the start of the trailing run of characters
   no pattern's charset can cross). `tests/test_stream.py` derives both from the
   compiled patterns via `re._parser` instead of trusting a comment. Note for anyone
   re-deriving this: the first property test, stated over match spans, passed 300/300
   against the leaking gate. Stated over the candidate *run* containing the match, the
   old rule failed 55 cases with a worst leak of 1125 characters.

Phase 2's `01-eval-harness` also gained `tests/test_gate.py` — `as_score` and
`aggregate` were extracted from `run_ragas` so the threshold arithmetic (NaN, missing
metric, out-of-range, boundary equality) is tested offline with no judge and no
network. `before/` carries the same file, failing by design.

`interview-loop/` (**W9**) carries no `pyproject.toml` on purpose — it is markdown only.
`verify-lessons.sh` finds lessons by locating `pyproject.toml` files, so the folder is
skipped with no special case.

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
