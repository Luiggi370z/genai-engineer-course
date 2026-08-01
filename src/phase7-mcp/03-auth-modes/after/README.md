# 7.3 Auth modes — reference

none (stdio) / bearer (team) / OAuth 2.1+PKCE (public), plus two validator tiers:
the policy dataclass in `src/auth.py` (audience checks, the confused-deputy trap)
and the real thing in `src/jwt_auth.py` — PyJWT verifying signature, expiry and
audience on actually-signed tokens, with a `BearerGate` middleware that guards a
lesson-02-style tool handler and returns auth failures as data, not crashes.

> **SDK version:** targets **`mcp>=2.0.0`** (spec 2026-07-28). v1 code
> (`from mcp.server.fastmcp import FastMCP`) will **not** run — see
> [`../SDK-V2-MIGRATION.md`](../SDK-V2-MIGRATION.md).
