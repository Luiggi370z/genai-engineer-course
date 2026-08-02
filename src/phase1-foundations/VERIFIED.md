# Verification stamp — `phase1-foundations`

**Last verified:** 2026-08-01
**How:** every `after/` reference passed `make check` (ruff + pyright + pytest) on this date,
and every `before/` scaffold passed lint + type with its tests failing by design.

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
