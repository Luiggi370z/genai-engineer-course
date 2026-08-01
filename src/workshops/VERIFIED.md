# Verification stamp — `workshops`

**Last verified:** 2026-07-31
**How:** every `after/` reference passed `make check` (ruff + pyright + pytest) on this date,
and every `before/` scaffold passed lint + type with its tests failing by design.

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
