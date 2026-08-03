# Verification stamp — `phase5-memory`

**Last verified:** 2026-08-01
**How:** every `after/` reference passed `make check` (ruff + pyright + pytest) on this
date, and every `before/` scaffold passed lint + type with its tests failing by design.

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
The integration tiers were additionally run for real: lesson 5.1 against `fastembed`
ONNX embeddings, 5.2 against `tiktoken`, and 5.4 against **both** Mem0 and LangMem with
Ollama serving `nomic-embed-text` locally — no API keys anywhere.

## What was verified against what

| Lesson | Library surface exercised | Version |
|---|---|---|
| 5.1 `01-memory-types` | `qdrant-client` payload filters: `MinShould` + `IsNullCondition` + `Range`, `PointIdsList` / `FilterSelector` deletes, `scroll` | qdrant-client 1.18.0 |
| 5.1 integration | `fastembed.TextEmbedding` (`BAAI/bge-small-en-v1.5`) | fastembed 0.8.0 |
| 5.2 `02-context-engineering` | `rapidfuzz` `token_set_ratio` + `default_process` | rapidfuzz 3.14.5 |
| 5.2 integration | `tiktoken.get_encoding("o200k_base")` | tiktoken 0.13.0 |
| 5.3 `03-supervisor-crew` | stdlib only — routing, delegation and cost are pure logic | — |
| 5.4 `04-memory-frameworks` | `mem0.Memory.from_config` / `add` / `search` / `get_all` / `delete` | **mem0ai 2.0.14** |
| 5.4 `04-memory-frameworks` | `langmem.create_manage_memory_tool` over `langgraph.store.memory.InMemoryStore` | **langmem 0.0.30**, langgraph 1.2.10 |

## Mem0 2.x moved the entity id into `filters`

`search` is `search(query, filters={"user_id": ...}, top_k=k)`. The `user_id=` keyword
that appears in most tutorials is the 1.x signature, and `top_k` is not `limit`. Writes
still take `user_id=` directly (`add(text, user_id=..., metadata=...)`), which makes the
asymmetry easy to miss.

Two more things worth knowing before you adopt it:

- **`infer=True` is the default.** `add()` sends your text to the configured LLM to be
  rewritten and merged with existing memories. That is Mem0's value proposition and an
  unbudgeted model call on the write path. The lesson passes `infer=False` so writes are
  deterministic and the contract suite is fast.
- **Expiry is native.** `add(..., expiration_date="YYYY-MM-DD")` plus `show_expired` on
  reads, and expiry is evaluated against the real clock — so a test cannot fast-forward
  time, it has to write with an expiry already in the past.

Import emits noise you did not cause: a PostHog analytics warning and two spaCy
"model not installed" lines. Harmless, and worth knowing before you go hunting.

## LangMem is a thin layer, and that is the point

`langmem` 0.0.30 was last released **2025-10-27** — nine months before this stamp. It
still resolves and works against `langgraph` 1.2.10 and `langchain` 1.3.x, which is
precisely because the durable part is LangGraph's store, not LangMem itself.

Two findings from running it:

- **A typed schema comes back nested.** `create_manage_memory_tool(..., schema=Fact)`
  stores `{"content": {"content": ..., "source": ..., "expires_at": ...}}`. Nothing
  documents that; you find it by printing `item.value`. The adapter's `_unwrap` absorbs
  it so nothing else in the codebase learns about the shape.
- **The manage tool returns a sentence, not an object.** A create yields
  `"created memory <uuid>"`, so the id has to be parsed out of the string.
- **There is no TTL concept** in LangMem or the LangGraph store. The adapter enforces
  expiry itself, which is the whole argument for owning the interface: the contract does
  not bend to whatever features a vendor shipped this quarter.

Writing and searching need no model at all, so the LangMem half of the integration tier
runs with nothing but the deterministic embedder.

## The pins, and why they are narrow

`mem0ai>=2.0,<3` and `langmem>=0.0.30,<0.1` — a `0.0.x` library gets a `<0.1` bound
because there is no promise anywhere that `0.0.31` keeps this surface. Both live in the
`integration` dependency group, so a vendor's transitive tree can never break the fast
tier that runs on every push.

If a lesson here fails to install, read the date above, then the lesson's
`pyproject.toml` — the pin says what it was built against. Upgrade one dependency at a
time and re-run `make check`.
