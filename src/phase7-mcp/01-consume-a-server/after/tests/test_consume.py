"""Real protocol calls, offline. v2's in-memory Client needs no transport."""
from mcp_types import TextContent

from src.consume import describe_server, lifecycle, run_session
from src.demo_server import build_demo_server


def text_of(block) -> str:
    """Content blocks are a union — narrow to text before reading .text."""
    assert isinstance(block, TextContent)
    return block.text


def test_five_beats_in_order():
    assert lifecycle() == ["connect", "initialize", "discover", "call", "close"]


async def test_call_a_tool_over_the_real_protocol():
    result = await run_session(build_demo_server(), "add", {"a": 2, "b": 40})
    assert "42" in text_of(result.content[0])
    assert result.is_error is False        # v2 fields are snake_case


async def test_discovery_lists_all_three_primitives():
    info = await describe_server(build_demo_server())
    assert info["tools"] == ["add"]
    assert info["resources"] == ["demo://greeting"]
    assert info["prompts"] == ["summarize"]


async def test_client_negotiates_the_2026_protocol():
    info = await describe_server(build_demo_server())
    assert info["protocol"].startswith("2026-")
