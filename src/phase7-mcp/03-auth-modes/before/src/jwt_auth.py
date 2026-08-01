"""TODO: real token validation with PyJWT — signature, expiry, audience, scope.

`auth.py` is the POLICY tier (which checks, and why). This module is the
CRYPTOGRAPHY tier: the same four checks against an actually-signed JWT, plus a
bearer gate for a lesson-02-style tool handler — the middleware a remote MCP
server needs the moment it leaves stdio.

The checks, in the order an attacker meets them:
  1. signature  — jwt.decode with the key and algorithms=["HS256"]
  2. exp        — jwt raises ExpiredSignatureError; report "expired"
  3. aud        — jwt raises InvalidAudienceError; report the audience trap
  4. scope      — YOUR check: OAuth scopes are one space-separated string

Reference: ../after/src/jwt_auth.py.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


def validate_jwt(
    token: str,
    *,
    key: str,
    audience: str,
    required_scope: str,
) -> tuple[bool, str]:
    """TODO 1: decode with PyJWT (signature + exp + aud all verified by the
    library — catch its specific exceptions and translate them into readable
    reasons), then check `required_scope` against the space-separated "scope"
    claim yourself. Return (ok, reason)."""
    raise NotImplementedError


Handler = Callable[..., Any]


@dataclass(frozen=True)
class BearerGate:
    """TODO 2: middleware. gate(handler) returns a guarded handler that takes
    the request headers first: no/invalid Bearer -> {"error": "unauthorized:
    <reason>"} (data, not an exception — an MCP client reads tool results);
    valid -> call the handler through."""

    key: str
    audience: str
    required_scope: str

    def __call__(self, handler: Handler) -> Handler:
        raise NotImplementedError
