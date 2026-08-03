# 7.1 Consume a server (do this first)

**Goal.** Be an MCP client before you build a server — implement the five protocol beats (connect, initialize, discover, call, close) with the v2 SDK (`mcp>=2.0.0`), so when something later breaks you know which side of the wire to blame. `src/demo_server.py` ships complete as the thing to point at.
**Prerequisite.** 4.2 Tools (what a tool schema is and why the model reads it).
**Effort.** ~30 min to green on the fast tests · no integration tier · ~50 min realistic first pass.

## Do this

```bash
make setup && make test     # 4 failing tests — read them, they are the spec
$EDITOR src/consume.py      # FIVE_BEATS, lifecycle, run_session, describe_server
make check                  # green: ruff + pyright + pytest, all offline
```

## What the first failure means

`test_five_beats_in_order` fails first: `lifecycle()` raises `NotImplementedError` and `FIVE_BEATS` is an empty list. Name the five beats in order, then move to the real work — `run_session` and `describe_server` open a v2 `Client` against the demo server and make genuine protocol calls, no transport and no network.

## Done when

- [ ] `make check` is green (lint, types, fast tests).
- [ ] `test_call_a_tool_over_the_real_protocol` passes: `run_session` calls the demo server's `add` tool over the protocol and the result carries `is_error is False` (v2 fields are snake_case).
- [ ] `test_client_negotiates_the_2026_protocol` passes: `describe_server` reports the negotiated protocol version from initialization.

## Stuck?

1. The v2 `Client` takes the server *object* directly — `Client(build_demo_server())` — and the same code would work with a URL or any transport. `async with` handles connect/initialize/close for you.
2. Inside the context manager: `await client.call_tool(name, args)` for `run_session`; for `describe_server`, combine `list_tools()`, `list_resources()`, `list_prompts()`, and the initialize result (server name + `protocol_version`) into the dict the test expects.

No integration lane: v2's in-memory `Client` already makes real protocol calls — the fast tests exercise the actual wire messages offline.
