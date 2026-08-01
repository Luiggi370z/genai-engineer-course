"""TODO: implement MCP auth selection + token validation.

- recommend(deployment): map personal/local -> none, team/internal -> bearer,
  public/saas -> oauth2.1+pkce.
- validate(token, this_server_uri, required_scope): reject expired tokens, WRONG
  AUDIENCE (RFC 8707), and missing scopes.
- call_upstream_correctly(client_token): must NOT forward the client's token
  (confused deputy) — obtain your own.

Reference: ../after/src/auth.py.
"""
from __future__ import annotations

from dataclasses import dataclass


def recommend(deployment: str) -> str:
    raise NotImplementedError  # TODO 1


@dataclass
class Token:
    subject: str
    audience: str
    scopes: tuple[str, ...]
    expired: bool = False


def validate(token: Token, this_server_uri: str, required_scope: str) -> tuple[bool, str]:
    raise NotImplementedError  # TODO 2


def call_upstream_correctly(client_token: Token) -> str:
    raise NotImplementedError  # TODO 3
