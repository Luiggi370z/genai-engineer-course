"""Optional Bearer-JWT auth for the service — the phase 7.3 checks, applied here.

Off by default: without ASSISTANT_JWT_SECRET the service stays a zero-key local
demo and every request runs as the anonymous "local" identity. With the secret
set, every mutating endpoint demands a token that passes the same four checks a
remote MCP server performs (see phase7-mcp/03-auth-modes):

  1. signature — minted with our key, not assembled by hand
  2. exp       — not expired
  3. aud       — issued FOR THIS service, not passed through from another
  4. scope     — grants the specific capability being exercised

The verified `sub` claim becomes the caller's identity — the hook that memory
namespacing and the audit log hang off.
"""
from __future__ import annotations

import jwt

ANONYMOUS = "local"


def validate_token(
    token: str, *, key: str, audience: str, required_scope: str
) -> tuple[bool, str, dict]:
    """PyJWT verifies signature/expiry/audience; the scope claim is ours to check
    (OAuth scopes are a space-separated string — a detail every hand-rolled
    validator forgets). Returns (ok, reason, claims)."""
    try:
        claims = jwt.decode(token, key, algorithms=["HS256"], audience=audience)
    except jwt.ExpiredSignatureError:
        return False, "expired", {}
    except jwt.InvalidAudienceError:
        return False, "wrong audience — token not issued for this service", {}
    except jwt.InvalidTokenError as exc:
        return False, f"invalid token: {exc}", {}
    if required_scope not in str(claims.get("scope", "")).split():
        return False, f"missing scope '{required_scope}'", {}
    return True, "ok", claims


def identity_from(
    authorization: str,
    *,
    secret: str | None,
    audience: str,
    required_scope: str,
) -> tuple[bool, str, str]:
    """Resolve a request's identity. Returns (ok, reason, subject).

    With auth disabled (no secret) everyone is ANONYMOUS and always allowed —
    the demo path. With auth enabled, a missing or failing token is rejected
    and the caller's identity is the token's verified `sub`."""
    if not secret:
        return True, "auth disabled", ANONYMOUS
    if not authorization.lower().startswith("bearer "):
        return False, "missing bearer token", ""
    token = authorization.split(" ", 1)[1]
    ok, reason, claims = validate_token(
        token, key=secret, audience=audience, required_scope=required_scope
    )
    if not ok:
        return False, reason, ""
    return True, "ok", str(claims.get("sub", ANONYMOUS))
