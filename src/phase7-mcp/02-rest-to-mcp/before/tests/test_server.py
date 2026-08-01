"""Real protocol tests: an in-memory Client drives the actual server. No transport.

This is the big v2 testing win — in v1 you could only unit-test the tool functions;
now the test exercises discovery, schema generation and dispatch for real.
"""
from mcp import Client
from mcp_types import TextContent, TextResourceContents  # v2: wire types, own package

from src.server import _get_weather, _list_cities, build_server


def text_of(block) -> str:
    """Content blocks are a union (text/image/audio/resource) — narrow to text."""
    assert isinstance(block, TextContent)
    return block.text


def resource_text(block) -> str:
    """Resources use their own content type: TextResourceContents (not TextContent)."""
    assert isinstance(block, TextResourceContents)
    return block.text


def test_plain_functions_still_unit_test_normally():
    assert _get_weather("Lima")["temp_c"] == 19
    assert "error" in _get_weather("Atlantis")
    assert _list_cities() == sorted(_list_cities())


async def test_all_three_tools_are_discoverable():
    async with Client(build_server()) as c:
        names = {t.name for t in (await c.list_tools()).tools}
    assert names == {"get_weather", "compare", "is_jacket_weather"}


async def test_schema_is_generated_from_type_hints():
    """You never write JSON Schema — the SDK derives it from the signature."""
    async with Client(build_server()) as c:
        tool = next(t for t in (await c.list_tools()).tools if t.name == "compare")
    assert set(tool.input_schema["properties"]) == {"city_a", "city_b"}   # snake_case in v2


async def test_docstring_becomes_the_model_facing_description():
    async with Client(build_server()) as c:
        tool = next(t for t in (await c.list_tools()).tools if t.name == "get_weather")
    assert tool.description and "weather" in tool.description.lower()


async def test_calling_a_tool_over_the_protocol():
    async with Client(build_server()) as c:
        cold = await c.call_tool("is_jacket_weather", {"city": "Cusco"})   # 12C
        mild = await c.call_tool("is_jacket_weather", {"city": "Lima"})    # 19C
    assert "true" in text_of(cold.content[0]).lower()
    assert "false" in text_of(mild.content[0]).lower()
    assert cold.is_error is False


async def test_resource_and_prompt_round_trip():
    async with Client(build_server()) as c:
        res = await c.read_resource("weather://cities")
        p = await c.get_prompt("trip_prompt", {"city": "Tokyo"})
    assert "lima" in resource_text(res.contents[0])
    assert "Tokyo" in text_of(p.messages[0].content)
