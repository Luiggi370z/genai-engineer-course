# Verification stamp — `phase2-retrieval`

**Last verified:** 2026-08-01
**How:** every `after/` reference passed `make check` (ruff + pyright + pytest) on this date,
and every `before/` scaffold passed lint + type with its tests failing by design.

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

## RAGAS: one pin and one API, shared with phase 3

Lesson 2.1's optional judged tier and lesson 3.2 teach the same library, so they
carry the same pin (`ragas>=0.4,<0.5`, `langchain-community>=0.3.27,<0.4`) and the
same API surface: metrics from **`ragas.metrics.collections`**, judge from
`ragas.llms.llm_factory` over an `openai.AsyncOpenAI` client, one sample per
`score()` call. Verified against **ragas 0.4.3** on 2026-07-31; the details of the
move and the langchain-community trap live in `../phase3-evals/VERIFIED.md`.

They used to disagree — 2.1 sat on the pre-0.4 `evaluate()` surface under a loose
`ragas>=0.2,<1`, which resolved to 0.4 and kept working because the old import
path is deprecated rather than removed. Nothing failed; the course just taught two
APIs for one library. `check-claims` now fails the build on both halves of that:
a second pin for a watched package, and a retired import path anywhere in `src/`.
