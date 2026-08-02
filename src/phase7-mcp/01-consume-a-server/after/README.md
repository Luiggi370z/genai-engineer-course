# 7.1 Consume a server — reference (SDK v2)

The five beats — **connect → initialize → discover → call → close** — against a real
server, with real protocol messages, entirely offline.

v2's `Client` takes an `MCPServer` object directly (in-memory, no transport), a URL
for Streamable HTTP, or any transport. Same code for all three; that's the protocol
doing its job. In-memory is the recommended way to test.

```bash
make check
```

> **SDK version:** these lessons target **`mcp>=2.0.0`** (spec 2026-07-28).
> v1 code (`from mcp.server.fastmcp import FastMCP`) will **not** run — see
> [`../SDK-V2-MIGRATION.md`](../SDK-V2-MIGRATION.md).

## Concept → framework primitive

There's no hand-rolled JSON-RPC layer to contrast here — the v2 SDK's in-memory
`Client` already makes real protocol calls, so `consume.py` *is* the production
code. The mapping that matters is between the five beats you memorized and the
SDK calls that actually perform them:

| the beat (what you internalized) | the primitive in `mcp` | what the SDK adds |
|---|---|---|
| connect + initialize | `async with Client(target) as client:` | handshake and protocol-version negotiation, and guaranteed teardown, for any target |
| discover | `client.list_tools()` / `.list_resources()` / `.list_prompts()` | typed result objects (`.tools`, `.resources`, `.prompts`) instead of hand-parsed JSON-RPC arrays |
| call | `client.call_tool(tool, args)` | a structured `CallToolResult` with `.content` blocks and `.is_error`, not a raw dict |
| close | the context manager's `__aexit__` | cleanup guaranteed even on error, across any transport |
| "same code, any transport" | `Client(server_object)` / `Client("http://host/mcp")` / `Client(transport)` | one client implementation; swap in-memory for HTTP or stdio with no code change |
| narrowing a content block before reading it | `TextContent` from `mcp_types`, checked with `isinstance` | a typed content union instead of duck-typed dict access |

**Two artifacts.** You now own two things that prove different skills: naming
the five beats from memory proves you understand the protocol's shape well
enough to know which side of the wire broke when something fails, and
`run_session`/`describe_server` prove you can drive the real `mcp` SDK against
an actual server — a bidirectional in-memory `MCPServer`, not a mock. The
interview skill is explaining what each beat costs you if you skip it, in terms
of the actual SDK call that implements it — this table is that explanation.
