# 5.3 Auth modes

Pick the right door per deployment and validate tokens correctly. Fill the TODOs in `src/auth.py`. Two traps to internalize: audience validation and never forwarding the client token upstream.

> **SDK version:** targets **`mcp>=2.0.0`** (spec 2026-07-28). v1 code
> (`from mcp.server.fastmcp import FastMCP`) will **not** run — see
> [`../SDK-V2-MIGRATION.md`](../SDK-V2-MIGRATION.md).
