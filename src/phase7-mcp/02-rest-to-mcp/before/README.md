# 7.2 REST → MCP

**Goal.** Wrap a REST-style weather service as an MCP server — 3 tools, 1 resource, 1 prompt — with the v2 SDK's `MCPServer`. You never write JSON Schema: type hints generate it and docstrings become the model-facing descriptions, so you write both *for the model*.
**Prerequisite.** 7.1 Consume a server (you'll test this server with the client moves you just learned).
**Effort.** ~30 min to green on the fast tests · no integration tier · ~50 min realistic first pass.

## Do this

```bash
make setup && make test     # 5 failing tests — read them, they are the spec
$EDITOR src/server.py       # build_server(): MCPServer("weather") + 3 tools, 1 resource, 1 prompt
make check                  # green: ruff + pyright + pytest, all offline
```

## What the first failure means

The plain-function unit test already passes — `_get_weather` and `_list_cities` ship complete. The first failure is `test_all_three_tools_are_discoverable`: `build_server()` raises `NotImplementedError`, so an in-memory `Client(build_server())` can't even list tools. The tests drive your server over the real protocol — discovery, generated schemas, dispatch — so they stay red until the decorators are wired, not just until the functions exist.

## Done when

- [ ] `make check` is green (lint, types, fast tests).
- [ ] Discovery finds exactly `get_weather`, `compare`, and `is_jacket_weather`, and `compare`'s generated `input_schema` has `city_a`/`city_b` properties derived from your type hints.
- [ ] `test_resource_and_prompt_round_trip` passes: `weather://cities` reads back the city list and `trip_prompt` renders with a city argument.

## Stuck?

1. `build_server()` must *return* the `MCPServer` without running it — the tests hand it straight to an in-memory `Client`. Decorate small wrappers around the private helpers: `@mcp.tool()`, `@mcp.resource("weather://cities")`, `@mcp.prompt()`.
2. The test names pin your tool signatures: `compare(city_a: str, city_b: str)` and `is_jacket_weather(city: str)` (cold below some threshold — Cusco at 12°C is jacket weather, Lima at 19°C is not). Give `get_weather` a docstring that says "weather"; the SDK ships it as the description the model reads.

No integration lane: the in-memory `Client` already exercises the real protocol — discovery, schema generation, and dispatch — entirely offline.
