# 5.2 REST → MCP

Wrap a REST API as an MCP server: 3 tools, 1 resource, 1 prompt. Fill
`build_server()` in `src/server.py`.

You never write JSON Schema — the SDK derives it from your type hints, and the
docstring becomes the description the model reads. The tests drive your server over
the **real protocol** using an in-memory client, so they fail until discovery and
dispatch actually work.

```bash
make setup && make test
```

> **SDK version:** targets **`mcp>=2.0.0`** (spec 2026-07-28). See
> [`../SDK-V2-MIGRATION.md`](../SDK-V2-MIGRATION.md).
