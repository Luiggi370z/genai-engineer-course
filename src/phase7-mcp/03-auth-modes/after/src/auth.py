"""Choose the right MCP auth per transport + trust boundary.

Three modes, and the rule that maps each to a deployment. Includes a token
validator that demonstrates the two classic traps: audience validation and the
confused-deputy (never forward the client's token upstream).
"""
from __future__ import annotations

from dataclasses import dataclass

# method -> (use when, main trap)
AUTH_MODES = {
    "none": ("local stdio server (OS user isolation); secrets via env vars",
             "hard-coding keys instead of reading env"),
    "bearer": ("internal/team remote server behind a gateway; every client known",
               "plaintext token in config; must be HTTPS, never in URLs"),
    "oauth2.1+pkce": ("public-facing remote server, or acting on behalf of users",
                      "forwarding the client token upstream (confused deputy)"),
}


def recommend(deployment: str) -> str:
    """Map a deployment to the right auth mode."""
    return {
        "personal": "none",
        "local": "none",
        "team": "bearer",
        "internal": "bearer",
        "public": "oauth2.1+pkce",
        "saas": "oauth2.1+pkce",
    }[deployment]


@dataclass
class Token:
    subject: str
    audience: str      # which server this token was issued FOR
    scopes: tuple[str, ...]
    expired: bool = False


def validate(token: Token, this_server_uri: str, required_scope: str) -> tuple[bool, str]:
    """A resource server validates a Bearer/OAuth token before serving."""
    if token.expired:
        return False, "expired"
    if token.audience != this_server_uri:      # RFC 8707 audience check
        return False, "wrong audience — token not issued for this server"
    if required_scope not in token.scopes:
        return False, "missing scope"
    return True, "ok"


def call_upstream_correctly(client_token: Token) -> str:
    """Confused-deputy safe: obtain a SEPARATE token, never forward the client's."""
    # WRONG: use client_token to call GitHub/etc. (token passthrough — forbidden)
    # RIGHT: exchange for our own service token scoped to the upstream call.
    return "obtained our own upstream token (did NOT forward the client's)"
