# The GenAI Engineer Workbook — Companion Code

Runnable `before/` and `after/` code for every exercise and workshop in the course.
`before/` is your starting scaffold (with `TODO`s); `after/` is a working reference.

**Attempt before you read.** Write your version, run `make check`, and open `after/`
only once it passes or you are genuinely stuck — then diff the two, because the diff
is the lesson. A solution you have read is indistinguishable, to you, from one you
could have written, and the whole `before/` tree exists to keep that distinction
available to you.

## How each lesson works

Every lesson folder is standalone and uses the same toolchain:

```bash
cd phase1-foundations/01-universal-client/before
make setup             # uv sync — create the venv, install deps
make lint              # ruff
make type              # pyright
make test              # pytest — fast, offline, deterministic
make check             # all three (what CI runs)
make test-integration  # opt-in: real models/services (downloads weights, needs Ollama)
```

## Two test tiers (and why)

`make test` must stay **fast, offline and deterministic** so it can run on every
commit — it uses real libraries and real APIs (e.g. `QdrantClient(":memory:")`)
with fixture data. `make test-integration` runs the same code against **real
models** (local ONNX embedders, a reranker, an Ollama judge). Splitting the two is
not a shortcut, it is how production repos are actually structured.

## The retrieval stack these lessons use

You wire libraries together; you do **not** implement algorithms:

| Layer | Package |
|---|---|
| keyword / sparse | `rank_bm25`, or `fastembed` `Qdrant/bm25` |
| dense / semantic | `fastembed` `BAAI/bge-small-en-v1.5` (local ONNX) |
| store + fusion | `qdrant-client` — `Prefetch` ×2 + `FusionQuery(Fusion.RRF)` |
| rerank | `fastembed` `TextCrossEncoder` (`BAAI/bge-reranker-base`) |
| chunking | `langchain-text-splitters` |
| eval | `ragas` (LLM judge) + `rapidfuzz` (fast offline gate) |
| memory | your own store on `qdrant-client`, plus `mem0ai` / `langmem` adapters |

Requirements: **Python 3.11 through 3.14** (`>=3.11,<3.15`, and CI proves both ends —
`./verify-lessons.sh --python 3.11` runs the set on the floor),
[uv](https://docs.astral.sh/uv/), and (for most lessons)
[Ollama](https://ollama.com) **installed on your machine** so everything works with
**zero API keys**.
`phase4-agents/04-framework-bakeoff` is the single exception: it pins **3.12** in its own
`pyproject.toml` (CrewAI's tree does not build on newer) and uv fetches that interpreter
for that lesson alone.
Pull the models the course uses once:

```bash
ollama pull qwen3.5:9b          # small chat / tool-calling model
ollama pull nomic-embed-text    # embeddings
ollama pull qwen3-coder:30b     # eval judge (Phase 3) — any capable local model works
ollama pull llama-guard3:8b     # guard model (Phase 6)
```

Install Ollama on the host, never in a container — Docker Desktop passes no GPU
through, and the same 9B that answers in a second on your laptop takes two minutes
inside the VM. Phase 8's stack keeps its infrastructure in compose and reaches your
Ollama at `host.docker.internal:11434`.

Hosted providers are optional everywhere — set `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`
only if you want to run the hosted path. The capstone picks one explicitly with
`ASSISTANT_PROVIDER=ollama|openai|anthropic|offline`; unset means Ollama when
`OLLAMA_HOST` is set and the offline stitcher otherwise, and naming a hosted provider
without its key fails the boot rather than quietly answering from the fallback.

## The nine workshops

Every phase ends in one. Workshops **2–8** build a single personal assistant that
grows across the course, which is why they share one folder — you finish with one
system you can defend end to end, not eight demos. Workshops **1** and **9** bookend
it: the tool you measure with, and the loop that turns the result into offers.

| # | Workshop | Ends phase | What it adds | Files |
|:-:|----------|:----------:|--------------|-------|
| 1 | Model bench        | 1 | A CLI that benches providers on one real task, ranked by cost per successful parse | `workshops/model-bench/` |
| 2 | RAG service        | 2 | A hybrid-retrieval core the assistant can query | `rag.py` |
| 3 | Eval suite + gate  | 3 | Golden set, injectable judge, calibration, CI gate | `evals.py` |
| 4 | Personal assistant | 4 | The agent core: tools (email, news, telegram, calendar) + HITL | `tools.py`, `agent.py` |
| 5 | Memory + crew      | 5 | Memory with provenance + TTL, budgeted context, tiered delegation | `memory.py`, `crew.py` |
| 6 | Hardened assistant | 6 | Guardrails, spotlighting, least-privilege, red-team CI | `guardrails.py` |
| 7 | Your own MCP       | 7 | An MCP server, consumed by the assistant via discovery | `mcp_client.py` |
| 8 | Deployed stack     | 8 | OTel spans around the loop and every tool, answer cache with refusal rules — plus the capstone: a FastAPI composition root wiring every layer, real adapters (Qdrant/Ollama/MCP/OTLP) behind env vars, SQLite memory, an MCP server, a Docker image | `observe.py`, `cache.py`, `service.py`, `api.py`, `core.py`, `adapters.py` |
| 9 | Interview loop     | 9 | No code — a scored design-mock rubric and a metrics worksheet | `workshops/interview-loop/` |

Briefs live in `workshops/assistant/WORKSHOP-*.md`, one per layer, plus
`workshops/model-bench/WORKSHOP-MODEL-BENCH.md` and
`workshops/interview-loop/WORKSHOP-INTERVIEW-LOOP.md`.

## Version pinning (read this before you file a bug)

Every dependency here carries an **upper bound** (e.g. `mcp>=2.0.0,<3`). That is
deliberate: on 2026-07-28 the MCP Python SDK shipped v2 and *removed*
`mcp.server.fastmcp`, breaking every unpinned v1 example overnight. Each phase has a
`VERIFIED.md` stamp saying when it last passed `make check`.

Three strengths of pin live in this repo, and the difference matters the first time a
lesson installs something newer than the stamp:

| Strength | Where | What it promises |
|---|---|---|
| **Bounded range** | every lesson's `pyproject.toml` | the newest release inside the range resolves and the API you were taught still exists. Not that you get the same bytes as anyone else. |
| **Recorded resolution** | a `VERIFIED.md` naming an exact version (`verified against ragas 0.4.3`) | what that dated run actually resolved to. It is evidence for bisecting a future break — nothing reinstalls it. |
| **Locked** | `workshops/assistant/after/uv.lock`, the only tracked lockfile | every transitive dependency by hash. `uv sync --frozen` gets the same tree on any machine. |

So: **the capstone's Python tree is locked; the lessons are version-bounded.** That is a
choice, not an omission. A lockfile per lesson would freeze 34 dependency trees that
exist to be upgraded — the course teaches you to raise a cap deliberately and re-run
`make check`, and a lockfile would hide the drift it wants you to practise on. The
capstone is locked because it is the one artifact that gets deployed, where "works on
my machine" is the failure being prevented.

Locked is not bit-identical, and the Dockerfile says why in more detail: its base images
are floating tags and the deployed stack pulls its models by tag, both on purpose, so a
rebuild collects Debian's security patches instead of pinning a known-vulnerable layer.
The lockfile fixes the Python tree by hash; the OS and the weights underneath it track
named update channels.

The interpreter follows the same rule: `>=3.11,<3.15`, and CI runs the whole lesson set
at **both ends** of that range on every push, so the bound is tested rather than
asserted. Run the floor yourself with `./verify-lessons.sh --python 3.11`.

The MCP lessons target **SDK v2** — see `phase7-mcp/SDK-V2-MIGRATION.md`.

## Lesson map

### Phase 1 · Speak Fluent LLM
- `01-universal-client` — one client across Anthropic/OpenAI/Google/Ollama
- `02-token-cost-meter` — count before (vendor counters), measure after (`usage`)
- `03-structured-extraction` — Pydantic/Instructor, hosted vs local
- `04-chunking` — fixed-size vs heading-aware splitters
- `05-embed-index` — embed + a numpy vector index + `search(query, k)`
- **Workshop → `workshops/model-bench`** (the model bench — the only standalone one)

### Phase 2 · Retrieval That Actually Works
- `01-eval-harness` — sliced golden set + the fast lexical gate (judged tier is opt-in)
- `02-hybrid-rerank` — BM25 + dense fused (RRF) + reranker
- `03-break-and-fix` — a pre-bugged RAG to debug with the playbook
- `04-contextual-chunks` — contextual retrieval, free on a local model
- **Workshop → `workshops/assistant`** (RAG service)

### Phase 3 · Prove It Works: Evals & Judges
- `01-golden-set` — dataset engineering: five slices, provenance, leakage + duplicate tests
- `02-llm-judge` — RAGAS judge behind an injectable protocol; harness fully testable offline
- `03-judge-calibration` — your labels vs the judge: agreement, Cohen's κ, threshold sweep
- `04-ci-regression-gate` — bars + per-slice baseline deltas, wired into GitHub Actions
- **Workshop → `workshops/assistant`** (eval suite + CI gate)

### Phase 4 · Agents on a Leash
- `01-react-from-scratch` — the loop, hard caps, local + hosted
- `02-tools` — three real tools, docstring-as-interface
- `03-hitl` — human-in-the-loop with LangGraph interrupt + checkpointer
- `04-framework-bakeoff` — the same tool-using agent in real LangGraph / Pydantic AI
  / CrewAI, scored on six dimensions from measurements (and honest about the ties)
- **Workshop → `workshops/assistant`** (personal assistant)

### Phase 5 · Agents That Remember & Collaborate
- `01-memory-types` — working / episodic / semantic / procedural behind one interface
- `02-context-engineering` — keep · compress · evict · park under a hard token budget
- `03-supervisor-crew` — supervisor + workers, tiered, cost-logged, delegation asserted
- `04-memory-frameworks` — Mem0 and LangMem adapters against one contract suite
- **Workshop → `workshops/assistant`** (memory + research crew)

### Phase 6 · Whiteboard It & Defend It
- `WORKSHEET.md` — the 45-minute system-design mock
- `01-red-team` — attack your own assistant (the catalog)
- `02-cost-model` — $/query with caching + routing
- **Workshop → `workshops/assistant`** (hardened assistant)

### Phase 7 · MCP: The Universal Tool Port
- `01-consume-a-server` — be a client first (the five beats)
- `02-rest-to-mcp` — wrap a REST API as an MCP server (FastMCP)
- `03-auth-modes` — stdio / Bearer / OAuth 2.1 + PKCE
- **Workshop → `workshops/assistant`** (your MCP, used by the assistant)

### Phase 8 · Run It in Production
- `01-compose` — the capstone stack behind one `docker compose up`: pinned images, healthchecks, health-gated dependencies, one published port — plus structural checks over the parsed YAML
- `02-ci` — the merge policy as four independently failing gates (quality, safety, latency, cost) over a version-stamped report, with real `make eval` / `make redteam` / `make latency` / `make cost` targets and seeded regressions proving each gate can block. The repo-root workflow points the same CLI at a report generated from the capstone **image** on every push — `make gate` in `workshops/assistant/after` does it locally
- `03-deploy-observe` — OpenTelemetry spans read offline (OTLP export is one env var), plus the release lane: immutable SHA tags, a manifest that refuses a pasted key, four post-deploy smoke probes (including `/health`'s commit against the one just shipped), a rollback that halts rather than lying, and a verified SQLite backup. The judgement is unit-tested Python; `deploy/` is a Fly.io reference, gated behind `DEPLOY_LANE=fly` and not live-provisioned
- `04-cost-latency` — exact + semantic cache, a tier router with a ceiling, a P99 budget gate
- **Workshop → `workshops/assistant`** (deployed stack + capstone service)

The slow lane: `./verify-e2e.sh` (needs Docker) boots the composed stack under the
**secure profile** — every request carries a Bearer JWT — and proves it end to end:
tier report, an unauthenticated request refused, grounded answer, abstention,
injection containment, approval gating bound to the approving subject, an MCP call
over the wire, two authenticated callers whose memories never cross, spans recorded,
and (via the observability overlay) the same spans arriving at an otel-collector
outside the process. `verify-lessons.sh` stays offline and never runs it.

Where it runs: not on push. Push CI builds the capstone image and validates the
compose overlays without booting anything; the scheduled `e2e` workflow runs the
whole suite with `--ci` against a small chat model, which proves the wiring and
not the answers; the unqualified local run is the release gate. Every lane says
which one it is in its own output.

A full pass is about forty-five seconds, so `verify-e2e.sh` also takes `--list`,
`--from N`, `--only N` and `--no-build` for the fix-and-re-prove loop. The checks
share one corpus, outbox and set of approvals on purpose, so a resumed run only
means something against volumes a full run has already filled; the unqualified
`./verify-e2e.sh` is the claim.

The model answers from **your machine**, not from a container. That is not a
convenience — it is the difference between forty-five seconds and twelve minutes.
Docker Desktop gives containers no GPU, so the same 9B runs at 0.52 tokens per
second inside the VM against 81 on the host: 156x, same model, same laptop, decided
by which side of the boundary the accelerator is on. Compose keeps the
infrastructure; `host.docker.internal:11434` reaches the model. Worth reading
[Phase 8's
VERIFIED.md](phase8-deploy/VERIFIED.md#the-twenty-minutes-and-what-was-hiding-inside-them)
for how that number stayed hidden for so long: the suite spent most of its runtime
timing out and answering from the fallback composer, with every check green, because
"is the answer grounded" and "did the model write it" are different questions and only
the first was being asked. Check 4 now asserts the second one.

Because compose can neither start nor wait for a dependency on the host, check 0 is
a **preflight**: the daemon answers, both models are pulled, both are warm, and a
throwaway container can actually reach the host through `host-gateway`. It never
pulls anything for you — a 5.6 GB download is your decision, not a test's.

### Phase 9 · The GenAI Mindset
- `drill-deck` — the interview question bank as flashcards
- `funnel-tracker` — instrument your job search
- `resume` — metric-first bullet templates
- **Workshop → `workshops/interview-loop`** (the interview loop — markdown only, no code)

## License
MIT — use it, fork it, ship it.
