# MCP Python SDK v2 — what changed and why these lessons target it

These lessons target **`mcp>=2.0.0,<3`** (protocol revision **2026-07-28**).

The official SDK shipped v2.0 stable on 2026-07-28. It is a **rewrite, not a rename
with shims** — v1 import paths were removed, not deprecated. An unpinned `mcp`
install now resolves to v2, so v1 tutorial code fails immediately.

## The migration table

| v1 | v2 |
|---|---|
| `from mcp.server.fastmcp import FastMCP` | `from mcp.server import MCPServer` |
| `mcp.server.fastmcp.*` | `mcp.server.mcpserver.*` (old paths **removed**) |
| `mcp.types` | standalone **`mcp-types`** package, imported as `mcp_types` |
| camelCase wire fields | snake_case attributes: `tool.input_schema`, `result.is_error` |
| `McpError` | `MCPError` |
| WebSocket transport | removed |
| long-lived stateful sessions | **stateless request/response** |
| hand-rolled test transports | `Client(server_object)` — in-memory, no transport |

The decorator API carried over, so most of a port is the import line:

```python
from mcp.server import MCPServer      # v2

mcp = MCPServer("weather")

@mcp.tool()
def get_weather(city: str) -> dict:
    """Get current weather for a city."""
    ...
```

## The conceptual change that matters most

The 2026-07-28 spec moved MCP from a **stateful, bidirectional** protocol to
**stateless request/response**. In v1 a client opened a long-lived session and held
it. In v2 that's a compatibility path: `ServerSession` survives as a thin proxy and
one endpoint serves both protocol eras, but new code should not assume a persistent
connection.

**The five beats — connect → initialize → discover → call → close — are still the
right mental model for what a client does.** They simply no longer have to happen
inside one held-open connection.

## The testing upgrade (why v2 is better for learning)

v2's universal client takes three kinds of target, and the same code works for all:

```python
Client(server_object)        # in-memory, no transport  <- use this in tests
Client("http://host/mcp")    # Streamable HTTP          <- remote servers
Client(transport)            # any transport ctx manager <- e.g. stdio
```

In v1 you could only unit-test your tool *functions*. In v2 your tests drive the
**real protocol** — discovery, generated schemas, dispatch — with no network and no
subprocess. Every test in these lessons does exactly that.

## Two different projects both called "FastMCP"

- **FastMCP 1.0** — the class contributed into the official `mcp` package in 2024.
  That is the one v2 renamed to `MCPServer`.
- **Standalone FastMCP** — Jeremiah Lowin's separate project (now under PrefectHQ),
  which reached **3.0 GA on 2026-02-18** and has its own roadmap. `pip install fastmcp`.

Same name, different projects, actively diverging. When you read a tutorial, check
which one it means. These lessons use the **official SDK**.

## Pinning

Pin the major version and upgrade deliberately:

```toml
dependencies = ["mcp>=2.0.0,<3"]
```

Official migration guide: <https://github.com/modelcontextprotocol/python-sdk>
