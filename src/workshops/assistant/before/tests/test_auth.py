"""The optional JWT gate, exercised entirely offline: tokens are minted with the
same secret the service validates against, so every accept/reject path runs in
the fast tier with no identity provider anywhere."""

import time

import jwt
from fastapi.testclient import TestClient

from assistant.api import create_app
from assistant.settings import Settings

SECRET = "test-secret-with-at-least-32-bytes!!"  # HS256 wants >=32 bytes of key
AUDIENCE = "assistant"


def secured_client() -> TestClient:
    return TestClient(
        create_app(Settings(jwt_secret=SECRET, jwt_audience=AUDIENCE)),
        raise_server_exceptions=False,
    )


def mint(scope: str, *, key: str = SECRET, audience: str = AUDIENCE,
         expires_in: int = 300, sub: str = "alice") -> str:
    return jwt.encode(
        {"sub": sub, "aud": audience, "scope": scope,
         "exp": int(time.time()) + expires_in},
        key, algorithm="HS256",
    )


def test_without_a_secret_the_zero_key_demo_path_stays_open():
    c = TestClient(create_app(Settings()))
    assert c.post("/ask", json={"question": "hello"}).status_code == 200


def test_a_missing_token_is_rejected_when_auth_is_on():
    response = secured_client().post("/ask", json={"question": "hello"})
    assert response.status_code == 401
    assert "bearer" in response.json()["detail"].lower()


def test_a_valid_token_with_the_right_scope_is_accepted():
    c = secured_client()
    headers = {"Authorization": f"Bearer {mint('assistant:ask')}"}
    assert c.post("/ask", json={"question": "hello"}, headers=headers).status_code == 200


def test_an_expired_token_is_rejected():
    c = secured_client()
    headers = {"Authorization": f"Bearer {mint('assistant:ask', expires_in=-10)}"}
    response = c.post("/ask", json={"question": "hello"}, headers=headers)
    assert response.status_code == 401
    assert "expired" in response.json()["detail"]


def test_a_token_for_another_audience_is_rejected():
    # The RFC 8707 passthrough trap: a token minted for some OTHER service must
    # not open this one, even though the signature and expiry check out.
    c = secured_client()
    headers = {"Authorization": f"Bearer {mint('assistant:ask', audience='other-api')}"}
    response = c.post("/ask", json={"question": "hello"}, headers=headers)
    assert response.status_code == 401
    assert "audience" in response.json()["detail"]


def test_a_token_missing_the_endpoint_scope_is_rejected():
    c = secured_client()
    # can ask, but /approve demands assistant:approve
    headers = {"Authorization": f"Bearer {mint('assistant:ask')}"}
    response = c.post("/approve", json={"tool": "send_telegram"}, headers=headers)
    assert response.status_code == 401
    assert "scope" in response.json()["detail"]


def test_a_forged_token_is_rejected():
    c = secured_client()
    wrong = "a-different-32-byte-signing-key!!!!!"
    headers = {"Authorization": f"Bearer {mint('assistant:ask', key=wrong)}"}
    assert c.post("/ask", json={"question": "hello"}, headers=headers).status_code == 401


def test_every_mutating_endpoint_is_behind_the_gate():
    c = secured_client()
    assert c.post("/ingest", json={"docs": ["x"]}).status_code == 401
    assert c.post("/ask", json={"question": "x"}).status_code == 401
    assert c.post("/ask/stream", json={"question": "x"}).status_code == 401
    assert c.post("/approve", json={"tool": "x"}).status_code == 401
    # /health stays open: probes and dashboards should not need a token
    assert c.get("/health").status_code == 200
