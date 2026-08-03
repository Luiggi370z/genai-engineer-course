# Verification stamp — `phase1-foundations`

**Last verified:** 2026-08-01
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

## What changed on 2026-07-31

Lessons 03 and 05 were reworked so their `before/` scaffolds actually fail (they used to
pass, which made the TODO optional). The fix in both cases was **dependency injection**
rather than more tests: `extract_invoice` now takes an `Extractor` and `VectorIndex` takes
an `Embedder`, so `extract_all` / `violation_rate` and `search` are testable with a fake
and the tests exercise the student's code instead of the scaffold's. A side effect worth
knowing: these two lessons no longer need Ollama for their fast tier.

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
