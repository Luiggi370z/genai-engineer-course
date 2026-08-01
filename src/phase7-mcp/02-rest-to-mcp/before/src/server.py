"""TODO: wrap this REST service as an MCP server using the v2 SDK.

    from mcp.server import MCPServer      # v2 (v1's FastMCP path is GONE)
    mcp = MCPServer("weather")

    @mcp.tool()
    def get_weather(city: str) -> dict:
        \"\"\"Get current weather for a city. Use when asked about weather.\"\"\"
        ...

    @mcp.resource("weather://cities")   # read-only data
    @mcp.prompt()                       # reusable prompt template

Build 3 tools, 1 resource, 1 prompt. Docstrings + type hints ARE the interface —
the SDK generates the JSON Schema from them, so write them for the model.

Return the server from build_server() (don't run it) so tests can drive it
in-memory with `Client(build_server())`.

Reference: ../after/src/server.py
"""
from __future__ import annotations

from mcp.server import MCPServer

_WEATHER = {
    "lima": {"temp_c": 19, "condition": "cloudy"},
    "tokyo": {"temp_c": 24, "condition": "clear"},
    "cusco": {"temp_c": 12, "condition": "cold"},
}


def _get_weather(city: str) -> dict:
    return _WEATHER.get(city.lower(), {"error": f"no data for {city!r}"})


def _list_cities() -> list[str]:
    return sorted(_WEATHER)


def build_server() -> MCPServer:
    """TODO: create MCPServer("weather") + 3 tools + 1 resource + 1 prompt."""
    raise NotImplementedError
