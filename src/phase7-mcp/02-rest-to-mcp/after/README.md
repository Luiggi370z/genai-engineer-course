# 5.2 REST → MCP — reference (SDK v2)

A `MCPServer` exposing 3 tools, a resource and a prompt over a REST service.

**What v2 changed:** `FastMCP` → `MCPServer`; `mcp.server.fastmcp` is removed;
schema fields are snake_case (`tool.input_schema`, `result.is_error`).

**The testing win:** an in-memory `Client(build_server())` drives the real protocol —
discovery, generated schemas and dispatch — with no transport and no network. In v1
you could only unit-test the raw functions.

```bash
make check
npx @modelcontextprotocol/inspector uv run python -m src.server   # manual poke
```

> **SDK version:** targets **`mcp>=2.0.0`** (spec 2026-07-28). See
> [`../SDK-V2-MIGRATION.md`](../SDK-V2-MIGRATION.md).
