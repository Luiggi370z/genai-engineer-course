"""Wrap a REST API as an MCP server with the v2 SDK: 3 tools, a resource, a prompt.

v2 renamed the high-level class: `FastMCP` -> `MCPServer`, and the old
`mcp.server.fastmcp` path is GONE (removed, not deprecated). The decorator API
carried over almost unchanged, so a v1 port is mostly the import line.

Your tool docstrings and type hints ARE the interface the model programs against —
the SDK generates the JSON Schema from them. Write them like prompts.
"""
from __future__ import annotations

from mcp.server import MCPServer

# --- the underlying "REST" service, stubbed so the lesson runs offline ---
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
    """Build the MCP server. Returned (not run) so tests can drive it in-memory."""
    mcp = MCPServer("weather")

    @mcp.tool()
    def get_weather(city: str) -> dict:
        """Get current weather for a city. Use when asked about weather or temperature.

        Args:
            city: city name, e.g. "Lima".
        """
        return _get_weather(city)

    @mcp.tool()
    def compare(city_a: str, city_b: str) -> dict:
        """Compare the temperature of two cities. Use for 'warmer/colder' questions."""
        a, b = _get_weather(city_a), _get_weather(city_b)
        if "error" in a or "error" in b:
            return {"error": "unknown city"}
        return {"warmer": city_a if a["temp_c"] >= b["temp_c"] else city_b, "a": a, "b": b}

    @mcp.tool()
    def is_jacket_weather(city: str) -> dict:
        """Say whether a jacket is advisable (below 18C). Use for 'what should I wear'."""
        w = _get_weather(city)
        return w if "error" in w else {"jacket": w["temp_c"] < 18}

    @mcp.resource("weather://cities")
    def cities() -> str:
        """Read-only: the cities this server knows about."""
        return ", ".join(_list_cities())

    @mcp.prompt()
    def trip_prompt(city: str) -> str:
        """A reusable template for planning what to pack for a city."""
        return f"Given the weather in {city}, list three things I should pack."

    return mcp


if __name__ == "__main__":
    # stdio for a desktop host; use transport="streamable-http" to serve remotely.
    build_server().run()
