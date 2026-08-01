# 5.1 Consume a server — reference (SDK v2)

The five beats — **connect → initialize → discover → call → close** — against a real
server, with real protocol messages, entirely offline.

v2's `Client` takes an `MCPServer` object directly (in-memory, no transport), a URL
for Streamable HTTP, or any transport. Same code for all three; that's the protocol
doing its job. In-memory is the recommended way to test.

```bash
make check
```

> **SDK version:** these lessons target **`mcp>=2.0.0`** (spec 2026-07-28).
> v1 code (`from mcp.server.fastmcp import FastMCP`) will **not** run — see
> [`../SDK-V2-MIGRATION.md`](../SDK-V2-MIGRATION.md).
