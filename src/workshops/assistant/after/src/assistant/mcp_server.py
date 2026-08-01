"""A small MCP server the assistant can discover tools from — the other end of
mcp_client.py. Reuses the phase-7 lesson-02 pattern (mcp v2 SDK, MCPServer),
kept to a few read-only tools so the capstone has a real server to talk to over
`make test-integration` and Docker Compose.

Run it directly for stdio (`python -m assistant.mcp_server`) or serve it over
streamable HTTP for the composed stack (see build_server().run(...)).
"""
from __future__ import annotations

from typing import Any

# Stubbed "reference" data so the server runs offline; swap for a real backend.
_FACTS = {
    "refund window": "Approved refunds are processed within five business days.",
    "escalation": "Payments above ten thousand euro need two approvers.",
    "support hours": "Support is staffed 09:00-18:00 UTC on weekdays.",
}


def _lookup_fact(topic: str) -> dict:
    key = topic.strip().lower()
    if key in _FACTS:
        return {"topic": key, "fact": _FACTS[key]}
    return {"error": f"no fact for {topic!r}", "known": sorted(_FACTS)}


def build_server() -> Any:
    """Build (not run) the MCP server so tests can drive it in-memory."""
    from mcp.server import MCPServer

    mcp = MCPServer("assistant-knowledge")

    @mcp.tool()
    def lookup_fact(topic: str) -> dict:
        """Look up a company fact by topic. Use for policy/how-does-X questions.

        Args:
            topic: a short topic key, e.g. "refund window".
        """
        return _lookup_fact(topic)

    @mcp.tool()
    def list_topics() -> list[str]:
        """List the topics this knowledge server can answer. Use to discover scope."""
        return sorted(_FACTS)

    @mcp.tool()
    def word_count(text: str) -> dict:
        """Count the words in a piece of text. A safe, read-only utility tool."""
        return {"words": len(text.split())}

    @mcp.resource("knowledge://topics")
    def topics() -> str:
        """Read-only: the topics this server knows about."""
        return ", ".join(sorted(_FACTS))

    return mcp


if __name__ == "__main__":
    import os
    import sys

    if "--http" in sys.argv:
        # The composed stack (phase8 lesson 1): serve streamable HTTP at /mcp.
        build_server().run(
            transport="streamable-http",
            host="0.0.0.0",  # noqa: S104 — inside a container, the port stays on the compose network
            port=int(os.getenv("PORT", "8080")),
        )
    else:
        build_server().run()  # stdio, for a desktop host
