"""Be a client first — the five beats of an MCP conversation (SDK v2).

WHAT CHANGED IN 2026: the 2026-07-28 spec moved MCP from a stateful, bidirectional
protocol to **stateless request/response**, and SDK v2 replaced `FastMCP` with
`MCPServer`. The five beats below still describe what every client DOES; they just
no longer require one long-lived connection to be held open between them.

The v2 `Client` takes three kinds of target:
    Client(server_object)   -> in-memory, no transport at all  (best for tests)
    Client("http://host/mcp") -> Streamable HTTP                (remote servers)
    Client(transport)        -> any transport context manager   (e.g. stdio)
The SAME client code works against all three. That is the point of a protocol.
"""
from __future__ import annotations

from typing import Any

# The canonical order of any client session. Memorize it — it never changes,
# even though the transport underneath it might.
FIVE_BEATS = ["connect", "initialize", "discover", "call", "close"]


def lifecycle() -> list[str]:
    """The five beats, in order."""
    return list(FIVE_BEATS)


async def run_session(target: Any, tool: str, args: dict) -> Any:
    """Open a session against ANY target, discover what's there, call one tool.

    `target` can be an MCPServer object (in-memory), a URL string, or a transport.
    """
    from mcp import Client

    async with Client(target) as client:          # 1. connect + 2. initialize
        await client.list_tools()                 # 3. discover
        result = await client.call_tool(tool, args)  # 4. call
        return result                             # 5. close (context exit)


async def describe_server(target: Any) -> dict:
    """A tiny 'what can you do?' probe — discovery is the whole point of MCP."""
    from mcp import Client

    async with Client(target) as client:
        tools = await client.list_tools()
        resources = await client.list_resources()
        prompts = await client.list_prompts()
        info = client.server_info          # Optional until initialize() completes
        return {
            "server": info.name if info else "unknown",
            "protocol": client.protocol_version,
            "tools": [t.name for t in tools.tools],
            "resources": [str(r.uri) for r in resources.resources],
            "prompts": [p.name for p in prompts.prompts],
        }
