"""Operate-tier behavior, proven offline: adapters that die mid-request degrade
to the offline tier instead of 500ing, load is shed politely at the door, and a
replayed approval cannot authorize a second irreversible run."""

from fastapi.testclient import TestClient

from assistant.adapters import InMemoryRag
from assistant.api import create_app
from assistant.composers import ABSTAIN, offline_compose
from assistant.fallbacks import FallbackRag, fallback_composer, fallback_stream
from assistant.resilience import Policy
from assistant.settings import Settings

FAST = Policy(attempts=2, base_delay=0.0, timeout=None)


class ExplodingRag:
    """A Qdrant stand-in whose network died."""

    def add(self, docs, tenant="local"):
        raise ConnectionError("qdrant unreachable")

    def search(self, query, k=3, tenant="local"):
        raise ConnectionError("qdrant unreachable")


def degraded_client() -> TestClient:
    app = create_app(Settings())
    a = app.state.assistant
    a.rag = FallbackRag(
        ExplodingRag(), InMemoryRag(),
        lambda component, why: a.degraded.__setitem__(component, why),
        policy=FAST,
    )
    return TestClient(app)


# --- degraded operation -----------------------------------------------------


def test_a_dead_rag_backend_degrades_to_the_offline_tier():
    c = degraded_client()
    c.post("/ingest", json={"docs": ["approved refunds take five business days"]})
    body = c.post("/ask", json={"question": "how long do refunds take"}).json()
    assert "refunds" in body["answer"].lower(), "the warm standby answered"

    health = c.get("/health").json()
    assert health["status"] == "degraded"
    assert "rag" in health["degraded"]


def test_a_dead_composer_falls_back_to_offline_prose():
    def dead_model(goal, contexts, state):
        raise ConnectionError("ollama unreachable")

    seen: dict[str, str] = {}
    compose = fallback_composer(dead_model, seen.__setitem__, policy=FAST)
    assert compose("q", ["the fact"], []) == "the fact"
    assert "brain" in seen


def test_a_stream_that_dies_before_the_first_chunk_streams_offline_instead():
    def dead_stream(goal, contexts, state):
        raise ConnectionError("ollama unreachable")
        yield  # pragma: no cover

    seen: dict[str, str] = {}
    stream = fallback_stream(dead_stream, seen.__setitem__)
    assert "".join(stream("q", [], [])) == ABSTAIN
    assert "brain" in seen


def test_a_stream_that_stalls_before_the_first_chunk_falls_back_at_the_deadline():
    """Regression, caught live: a thinking model spent minutes reasoning before
    its first token and the unbounded stream just waited. Slow is a failure mode,
    not a different success mode — the deadline falls back like a crash does."""
    import time as _time

    def stalled_stream(goal, contexts, state):
        _time.sleep(5)  # far past the test's deadline — must not be waited out
        yield "too late"  # pragma: no cover

    seen: dict[str, str] = {}
    stream = fallback_stream(stalled_stream, seen.__setitem__, timeout=0.05)
    started = _time.monotonic()
    out = "".join(stream("what is the refund window", ["refund window is five days"], []))
    assert _time.monotonic() - started < 2.0, "the deadline was not enforced"
    assert "refund" in out, "the offline fallback answered from the evidence"
    assert "brain" in seen


def test_a_stream_that_stalls_mid_flight_truncates_instead_of_hanging():
    import time as _time

    def trickle_then_stall(goal, contexts, state):
        yield "first "
        _time.sleep(5)
        yield "never arrives"  # pragma: no cover

    seen: dict[str, str] = {}
    stream = fallback_stream(trickle_then_stall, seen.__setitem__, timeout=0.05)
    out = "".join(stream("q", [], []))
    assert out == "first ", "chunks already on the wire stay; the stall truncates"
    assert "brain" in seen, "the truncation is reported, not absorbed"


def test_the_degraded_composer_does_not_fabricate_grounding():
    """A vector store returns the nearest neighbours of ANY question. When the
    model tier is down, the offline fallback must not dress an unrelated snippet
    up as an answer — no shared content word, no answer."""
    unrelated = ["approved refunds are processed within five business days"]
    assert offline_compose("what is the ceo home postal address", unrelated, []) == ABSTAIN
    assert "refunds" in offline_compose("how long do refunds take", unrelated, [])


# --- load shedding ------------------------------------------------------------


def test_requests_beyond_the_burst_get_429():
    c = TestClient(create_app(Settings(rate_limit_rps=0.0001, rate_limit_burst=2)))
    assert c.post("/ask", json={"question": "one"}).status_code == 200
    assert c.post("/ask", json={"question": "two"}).status_code == 200
    assert c.post("/ask", json={"question": "three"}).status_code == 429


def test_requests_beyond_the_concurrency_cap_get_503():
    app = create_app(Settings(max_concurrency=1))
    c = TestClient(app)
    cap = app.state.cap
    assert cap.enter(), "occupy the only slot, as an in-flight request would"
    assert c.post("/ask", json={"question": "hello"}).status_code == 503
    cap.leave()
    assert c.post("/ask", json={"question": "hello"}).status_code == 200


def test_health_is_never_shed():
    c = TestClient(create_app(Settings(rate_limit_rps=0.0001, rate_limit_burst=1)))
    c.post("/ask", json={"question": "drain the bucket"})
    assert c.post("/ask", json={"question": "x"}).status_code == 429
    assert c.get("/health").status_code == 200, "probes must keep working under limit"


# --- approvals: one grant, one run; replays are no-ops -------------------------

SEND = {"question": "please message the team about the outage"}


def paused_call(c):
    """The exact call the assistant is waiting on, as the pause reports it."""
    return c.post("/ask", json=SEND).json()["pending"]


def approve(c, pending, headers=None):
    """Approve exactly that call.

    A grant is bound to the arguments, so authorizing a send means echoing back
    the ones the pause reported. That round trip IS the flow — a client that
    cannot name the call it is approving should not be approving it.
    """
    return c.post(
        "/approve",
        json={"tool": pending["tool"], "args": pending["args"]},
        headers=headers or {},
    )


def test_an_approval_authorizes_exactly_one_run():
    c = TestClient(create_app(Settings()))
    approve(c, paused_call(c))
    first = c.post("/ask", json=SEND).json()
    assert "ran: send_telegram" in first["audit"]
    second = c.post("/ask", json=SEND).json()
    assert second["pending"]["tool"] == "send_telegram", (
        "the grant was spent — a new send needs a new approval"
    )


def test_a_replayed_approval_does_not_grant_twice():
    c = TestClient(create_app(Settings()))
    headers = {"Idempotency-Key": "approve-outage-123"}
    pending = paused_call(c)
    first = approve(c, pending, headers).json()
    replay = approve(c, pending, headers).json()
    assert "replayed" not in first
    assert replay["replayed"] is True

    fired = c.post("/ask", json=SEND).json()
    assert "ran: send_telegram" in fired["audit"]
    paused = c.post("/ask", json=SEND).json()
    assert paused["pending"]["tool"] == "send_telegram", (
        "the retried approval must not have granted a second run"
    )


def test_two_distinct_approvals_grant_two_runs():
    c = TestClient(create_app(Settings()))
    pending = paused_call(c)
    approve(c, pending, {"Idempotency-Key": "a1"})
    approve(c, pending, {"Idempotency-Key": "a2"})
    assert "ran: send_telegram" in c.post("/ask", json=SEND).json()["audit"]
    assert "ran: send_telegram" in c.post("/ask", json=SEND).json()["audit"]
