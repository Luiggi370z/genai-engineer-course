"""The cryptography tier, tested with real signed tokens. Still offline: HS256
needs a shared secret, not a network."""
from __future__ import annotations

import time

import jwt
import pytest

from src.jwt_auth import BearerGate, validate_jwt

# HS256 wants >= 32 bytes of key (RFC 7518) — even lesson secrets get that right.
KEY = "lesson-secret-0123456789abcdef-0123456789abcdef"
AUD = "https://weather.internal"


def mint(
    *,
    key: str = KEY,
    audience: str = AUD,
    scope: str = "weather:read",
    expires_in: int = 600,
) -> str:
    return jwt.encode(
        {"sub": "alice", "aud": audience, "scope": scope, "exp": time.time() + expires_in},
        key,
        algorithm="HS256",
    )


def test_a_well_formed_token_passes_all_four_checks():
    ok, reason = validate_jwt(mint(), key=KEY, audience=AUD, required_scope="weather:read")
    assert (ok, reason) == (True, "ok")


def test_a_tampered_signature_is_rejected():
    forged = mint(key="attacker-key-0123456789abcdef-0123456789abcdef")
    ok, reason = validate_jwt(forged, key=KEY, audience=AUD, required_scope="weather:read")
    assert not ok and "invalid token" in reason


def test_an_expired_token_is_rejected():
    ok, reason = validate_jwt(
        mint(expires_in=-60), key=KEY, audience=AUD, required_scope="weather:read"
    )
    assert (ok, reason) == (False, "expired")


def test_a_token_for_another_server_is_rejected():
    # The RFC 8707 check that makes token passthrough fail loudly.
    ok, reason = validate_jwt(
        mint(audience="https://other.internal"), key=KEY, audience=AUD,
        required_scope="weather:read",
    )
    assert not ok and "audience" in reason


def test_scopes_are_space_separated_and_checked_individually():
    token = mint(scope="weather:read weather:compare")
    ok, _ = validate_jwt(token, key=KEY, audience=AUD, required_scope="weather:compare")
    assert ok
    ok, reason = validate_jwt(token, key=KEY, audience=AUD, required_scope="weather:admin")
    assert not ok and reason == "missing scope"


# --- the gate in front of a lesson-02-style tool handler --------------------


@pytest.fixture
def gate() -> BearerGate:
    return BearerGate(key=KEY, audience=AUD, required_scope="weather:read")


def get_weather(city: str) -> dict:
    return {"city": city, "temp_c": 19}


def test_the_gate_passes_a_valid_bearer_through_to_the_tool(gate):
    guarded = gate(get_weather)
    out = guarded({"authorization": f"Bearer {mint()}"}, city="Lima")
    assert out == {"city": "Lima", "temp_c": 19}


def test_the_gate_refuses_a_missing_header_as_data_not_a_crash(gate):
    out = gate(get_weather)({}, city="Lima")
    assert "unauthorized" in out["error"]


def test_the_gate_refuses_a_bad_token_and_names_the_reason(gate):
    out = gate(get_weather)(
        {"authorization": f"Bearer {mint(scope='weather:admin')}"}, city="Lima"
    )
    assert out["error"] == "unauthorized: missing scope"
