"""A minimal server so you have something real to point a client at."""
from __future__ import annotations

from mcp.server import MCPServer


def build_demo_server() -> MCPServer:
    mcp = MCPServer("demo")

    @mcp.tool()
    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    @mcp.resource("demo://greeting")
    def greeting() -> str:
        """A canned greeting."""
        return "hello from the demo server"

    @mcp.prompt()
    def summarize(topic: str) -> str:
        """A reusable summarize prompt."""
        return f"Summarize {topic} in three bullets."

    return mcp
