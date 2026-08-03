# Verification stamp — `phase2-retrieval`

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

## The judged tier is tested without the judge (2026-08-02)

`run_ragas` was one function that called the judge, read its scores and compared them
with the bars, so the only test that could touch the arithmetic needed an API key —
which meant in practice the arithmetic had no test, and `tests/test_integration.py`
asserted that keys were present rather than that numbers were right.

`as_score` (one metric's result → a validated float) and `aggregate` (per-question
results → mean per metric) are now pure functions, and `tests/test_gate.py` exercises
them offline: a `NaN` score, a metric the judge omitted, a value outside `0..1`, an
empty result set, and the boundary case where a mean lands exactly on its bar. Each of
those is a way a real RAGAS run has silently produced a passing gate. The integration
test still runs against a live judge and now asserts ranges and a pass/fail verdict
rather than key presence.

## The golden set is a floor, not a fixture size (2026-08-02)

`golden.jsonl` ships **6 rows** (3 semantic, 2 exact, 1 unanswerable) so the harness
runs on checkout. The assignment is **30**, learner-written, against their own corpus.
`test_golden_set_loads_with_slices` therefore asserts `>= 6` and a minimum per slice:
an `== 6` assertion turns doing the assignment into a red test, which teaches the
opposite of the lesson. Six rows cannot separate a real regression from noise, and the
README says so where a learner will read it before trusting a number.

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
