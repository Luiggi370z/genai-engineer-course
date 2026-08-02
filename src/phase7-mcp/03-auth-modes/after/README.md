# 7.3 Auth modes — reference

none (stdio) / bearer (team) / OAuth 2.1+PKCE (public), plus two validator tiers:
the policy dataclass in `src/auth.py` (audience checks, the confused-deputy trap)
and the real thing in `src/jwt_auth.py` — PyJWT verifying signature, expiry and
audience on actually-signed tokens, with a `BearerGate` middleware that guards a
lesson-02-style tool handler and returns auth failures as data, not crashes.

> **SDK version:** targets **`mcp>=2.0.0`** (spec 2026-07-28). v1 code
> (`from mcp.server.fastmcp import FastMCP`) will **not** run — see
> [`../SDK-V2-MIGRATION.md`](../SDK-V2-MIGRATION.md).

## Concept → framework primitive

| what you built (`auth.py`'s `validate()`) | the primitive in PyJWT (`jwt_auth.py`) | what PyJWT adds |
|---|---|---|
| `token.expired` — a bool you set by hand | `jwt.decode(token, key, algorithms=["HS256"])` raising `jwt.ExpiredSignatureError` off the real `exp` claim | expiry tied to a signed timestamp, not a flag nobody flips in production |
| `token.audience != this_server_uri` — a manual string compare | `jwt.decode(..., audience=audience)` raising `jwt.InvalidAudienceError` | the RFC 8707 check runs during decode itself — impossible to forget it |
| (no signature check exists — `Token` is a plain dataclass) | `jwt.decode(token, key, algorithms=["HS256"])` verifying the HMAC signature | cryptographic proof the token was minted by the key holder, not just assembled |
| `required_scope not in token.scopes` — a tuple membership check | `required_scope not in str(claims.get("scope", "")).split()` on the decoded `claims` | nothing — PyJWT doesn't validate scopes either; the same check now runs on trustworthy, signature-verified data |
| ad-hoc `False, "reason"` branches for malformed input | `except jwt.InvalidTokenError as exc:` catching every malformed/tampered case | one exception hierarchy instead of a growing list of hand-written edge cases |
| calling `validate()` inline before running a tool | `BearerGate`, a callable `@dataclass` wrapping any handler | reusable middleware in front of every tool, reading the header itself |

**Two artifacts.** You now own two things that prove different skills: `auth.py`
proves you understand *why* a resource server checks expiry, audience, and scope
— including the confused-deputy trap `call_upstream_correctly` guards against —
and `jwt_auth.py` proves you can operate the real cryptography: PyJWT's
`jwt.decode`, its specific exceptions, and a `BearerGate` guarding an actual
handler. The interview skill is naming which of the four checks PyJWT gives you
for free and which one — scope — is still on you. This table is that answer.
