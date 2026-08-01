"""TODO: be a client. Implement the five beats with the v2 SDK.

The v2 `Client` accepts three kinds of target and the SAME code works for all:
    Client(server_object)      -> in-memory, no transport (use this in tests)
    Client("http://host/mcp")  -> Streamable HTTP (remote)
    Client(transport)          -> any transport context manager

    from mcp import Client
    async with Client(target) as client:
        await client.list_tools()
        await client.call_tool(name, args)

Reference: ../after/src/consume.py
"""
from __future__ import annotations

from typing import Any

FIVE_BEATS: list[str] = []  # TODO 1: the five beats, in order


def lifecycle() -> list[str]:
    raise NotImplementedError  # TODO 2


async def run_session(target: Any, tool: str, args: dict) -> Any:
    """TODO 3: open a Client, discover, call one tool, return the result."""
    raise NotImplementedError


async def describe_server(target: Any) -> dict:
    """TODO 4: return {"server","protocol","tools","resources","prompts"}."""
    raise NotImplementedError
