"""Workshop 7 layer — the assistant gains tools from an MCP server by DISCOVERY.

The win condition: tools are listed at runtime and adapted into the agent's
registry, NOT hard-coded. Add a tool to the server, restart, the assistant can
use it. `discover` is injected (a fake in tests; a real ClientSession.list_tools
in production) so this runs offline.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from assistant.tools import Tool


def as_agent_tools(
    discovered: list[dict],
    invoker: Callable[[str, dict], Any],
) -> dict[str, Tool]:
    """Turn discovered MCP tool specs into agent Tools — no hand-coding per tool.

    Each spec: {"name", "description", "requires_approval"?, "required_args"?}.
    The invoker actually calls the MCP server (call_tool) at runtime.

    `required_args` comes from the server's own input schema, which is what lets
    planner.py treat a discovered tool exactly like a built-in one: it can tell
    whether it is able to fill the call.
    """
    registry: dict[str, Tool] = {}
    for spec in discovered:
        name = spec["name"]

        def make(n: str) -> Callable[..., Any]:
            def call(**kwargs: Any) -> Any:
                return invoker(n, kwargs)
            return call

        registry[name] = Tool(
            name=name,
            fn=make(name),
            requires_approval=bool(spec.get("requires_approval", False)),
            doc=spec.get("description", ""),
            required_args=tuple(spec.get("required_args", ())),
        )
    return registry


def extend_assistant(
    base_registry: dict[str, Tool],
    discovered: list[dict],
    invoker: Callable[[str, dict], Any],
) -> dict[str, Tool]:
    """Merge discovered MCP tools into the assistant's existing toolbox."""
    merged = dict(base_registry)
    merged.update(as_agent_tools(discovered, invoker))
    return merged
