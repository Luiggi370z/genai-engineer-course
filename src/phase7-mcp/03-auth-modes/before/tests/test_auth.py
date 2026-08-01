from src.auth import Token, recommend, validate


def test_recommendations_map_to_trust_boundary():
    assert recommend("personal") == "none"
    assert recommend("team") == "bearer"
    assert recommend("public") == "oauth2.1+pkce"


def test_audience_must_match():
    t = Token("alice", audience="https://other-server", scopes=("read",))
    ok, reason = validate(t, "https://my-server", "read")
    assert not ok and "audience" in reason


def test_expired_token_rejected():
    t = Token("alice", audience="https://my-server", scopes=("read",), expired=True)
    ok, _ = validate(t, "https://my-server", "read")
    assert not ok


def test_valid_token_passes():
    t = Token("alice", audience="https://my-server", scopes=("read", "write"))
    ok, reason = validate(t, "https://my-server", "write")
    assert ok and reason == "ok"


def test_missing_scope_rejected():
    t = Token("alice", audience="https://my-server", scopes=("read",))
    ok, _ = validate(t, "https://my-server", "admin")
    assert not ok
