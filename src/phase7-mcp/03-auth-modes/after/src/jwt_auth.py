"""Real token validation with PyJWT — signature, expiry, audience, scope.

`auth.py` holds the POLICY tier: a plain dataclass showing which checks a
resource server performs and why. This module is the CRYPTOGRAPHY tier: the
same four checks against an actually-signed JWT, plus a bearer gate that wires
them in front of a tool handler — the middleware you put on the lesson-02
server the moment it leaves stdio for a remote transport.

The checks, in the order an attacker meets them:
  1. signature  — the token was minted by the key holder, not assembled
  2. exp        — and hasn't outlived its welcome
  3. aud        — and was issued FOR THIS server (RFC 8707; the passthrough trap)
  4. scope      — and grants the specific capability being exercised
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import jwt


def validate_jwt(
    token: str,
    *,
    key: str,
    audience: str,
    required_scope: str,
) -> tuple[bool, str]:
    """The real version of auth.py's validate(): PyJWT verifies the signature,
    expiry and audience; we verify the scope claim ourselves (OAuth scopes are
    a space-separated string — a detail every hand-rolled validator forgets)."""
    try:
        claims = jwt.decode(token, key, algorithms=["HS256"], audience=audience)
    except jwt.ExpiredSignatureError:
        return False, "expired"
    except jwt.InvalidAudienceError:
        return False, "wrong audience — token not issued for this server"
    except jwt.InvalidTokenError as exc:
        return False, f"invalid token: {exc}"
    if required_scope not in str(claims.get("scope", "")).split():
        return False, "missing scope"
    return True, "ok"


Handler = Callable[..., Any]


@dataclass(frozen=True)
class BearerGate:
    """Gate a tool handler behind a Bearer JWT — middleware for a remote server.

    Usage mirrors the lesson-02 server: wrap each tool handler once,

        gate = BearerGate(key=SECRET, audience="https://weather.internal",
                          required_scope="weather:read")
        guarded = gate(get_weather)
        guarded(headers, city="Lima")

    Unauthorized calls return an error DICT rather than raising: to an MCP
    client, an auth failure is a tool result it can read, not a crashed server.
    """

    key: str
    audience: str
    required_scope: str

    def __call__(self, handler: Handler) -> Handler:
        def guarded(headers: dict[str, str], /, *args: Any, **kwargs: Any) -> Any:
            authorization = headers.get("authorization", "")
            if not authorization.lower().startswith("bearer "):
                return {"error": "unauthorized: missing bearer token"}
            ok, reason = validate_jwt(
                authorization.split(" ", 1)[1],
                key=self.key,
                audience=self.audience,
                required_scope=self.required_scope,
            )
            if not ok:
                return {"error": f"unauthorized: {reason}"}
            return handler(*args, **kwargs)

        return guarded
