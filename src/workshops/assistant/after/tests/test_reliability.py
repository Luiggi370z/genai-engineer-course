"""Operate-tier behavior, proven offline: adapters that die mid-request degrade
to the offline tier instead of 500ing, load is shed politely at the door, every
side effect survives a retry unchanged, and an irreversible call that crashes
mid-flight leaves a question rather than silence."""

import sqlite3
import sys
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from assistant import deadline
from assistant.adapters import InMemoryRag
from assistant.api import create_app
from assistant.composers import ABSTAIN, offline_compose
from assistant.fallbacks import FallbackRag, fallback_composer, fallback_stream
from assistant.idempotency import IdempotencyStore
from assistant.outbox import FAILED, PENDING, SENT, Outbox, recorded_registry
from assistant.resilience import Policy
from assistant.settings import Settings
from assistant.tools import REGISTRY, rewrap

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
    def dead_model(goal, contexts, state, memories=None):
        raise ConnectionError("ollama unreachable")

    seen: dict[str, str] = {}
    compose = fallback_composer(dead_model, seen.__setitem__, policy=FAST)
    assert compose("q", ["the fact"], [], []) == "the fact"
    assert "brain" in seen


def test_a_stream_that_dies_before_the_first_chunk_streams_offline_instead():
    def dead_stream(goal, contexts, state, memories=None):
        raise ConnectionError("ollama unreachable")
        yield  # pragma: no cover

    seen: dict[str, str] = {}
    stream = fallback_stream(dead_stream, seen.__setitem__)
    assert "".join(stream("q", [], [], [])) == ABSTAIN
    assert "brain" in seen


def test_a_stream_that_stalls_before_the_first_chunk_falls_back_at_the_deadline():
    """Regression, caught live: a thinking model spent minutes reasoning before
    its first token and the unbounded stream just waited. Slow is a failure mode,
    not a different success mode — the deadline falls back like a crash does."""
    import time as _time

    def stalled_stream(goal, contexts, state, memories=None):
        _time.sleep(5)  # far past the test's deadline — must not be waited out
        yield "too late"  # pragma: no cover

    seen: dict[str, str] = {}
    stream = fallback_stream(stalled_stream, seen.__setitem__, timeout=0.05)
    started = _time.monotonic()
    out = "".join(
        stream("what is the refund window", ["refund window is five days"], [], [])
    )
    assert _time.monotonic() - started < 2.0, "the deadline was not enforced"
    assert "refund" in out, "the offline fallback answered from the evidence"
    assert "brain" in seen


def test_a_stream_that_stalls_mid_flight_truncates_instead_of_hanging():
    import time as _time

    def trickle_then_stall(goal, contexts, state, memories=None):
        yield "first "
        _time.sleep(5)
        yield "never arrives"  # pragma: no cover

    seen: dict[str, str] = {}
    stream = fallback_stream(trickle_then_stall, seen.__setitem__, timeout=0.05)
    out = "".join(stream("q", [], [], []))
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


# --- idempotency: EVERY side effect, not just the approval ----------------------

DOC = {"docs": [{"text": "approved refunds take five business days", "source": "r.md"}]}


def test_a_retried_ingest_does_not_ingest_twice():
    """The failure this closes is the ordinary one: a client's request times out,
    the client cannot tell whether the server acted, so it asks again — and the
    corpus quietly holds two copies of the same page."""
    c = TestClient(create_app(Settings()))
    headers = {"Idempotency-Key": "batch-7"}
    first = c.post("/ingest", json=DOC, headers=headers).json()
    replay = c.post("/ingest", json=DOC, headers=headers).json()
    assert first["ingested"] == 1
    assert replay["replayed"] is True


def test_a_replay_returns_the_ORIGINAL_answer_not_a_receipt():
    """`{"replayed": true}` alone avoids the double effect and still breaks the
    client, which asked a question and got an acknowledgement. A retry has to be
    indistinguishable from the call it repeats — that is what the word means."""
    c = TestClient(create_app(Settings()))
    headers = {"Idempotency-Key": "batch-8"}
    first = c.post("/ingest", json=DOC, headers=headers).json()
    replay = c.post("/ingest", json=DOC, headers=headers).json()
    assert replay["ingested"] == first["ingested"]
    assert replay["rejected"] == first["rejected"]


def test_the_same_key_on_two_operations_does_not_collide():
    """Keys are chosen by clients, and "retry-1" is what every client picks. A
    single flat namespace lets a retried ingest swallow an approval."""
    c = TestClient(create_app(Settings()))
    headers = {"Idempotency-Key": "retry-1"}
    ingested = c.post("/ingest", json=DOC, headers=headers).json()
    approved = approve(c, paused_call(c), headers).json()
    assert ingested["ingested"] == 1
    assert "replayed" not in approved, "a different operation is a different key"
    assert approved["approval_id"]


def test_a_failed_operation_leaves_the_key_retryable():
    """Recording the key up front turns one transient failure into a permanent
    one: every retry cheerfully acknowledged, the effect never applied, nothing
    in the logs saying so."""
    app = create_app(Settings())
    a = app.state.assistant
    calls = {"n": 0}
    real_ingest = a.ingest

    def flaky_ingest(docs, subject):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ConnectionError("the index was not reachable")
        return real_ingest(docs, subject)

    a.ingest = flaky_ingest
    c = TestClient(app, raise_server_exceptions=False)
    headers = {"Idempotency-Key": "batch-9"}
    assert c.post("/ingest", json=DOC, headers=headers).status_code == 500
    assert c.post("/ingest", json=DOC, headers=headers).json()["ingested"] == 1


# --- the model call: bounded, or the request has no duration ---------------------


def fake_ollama(monkeypatch, seen):
    """Stand in for the `ollama` package, which the fast tier does not install.

    The adapters import it lazily precisely so this is possible: the shape of the
    request we send a model is worth testing without a model, because it is a
    property of our code and not of theirs."""

    class FakeClient:
        def __init__(self, host, timeout=None):
            seen["host"] = host

        def generate(self, **kwargs):
            seen.update(kwargs)
            if kwargs.get("stream"):
                return iter([{"response": "five business "}, {"response": "days"}])
            return {"response": "  five business days\n"}

    monkeypatch.setitem(sys.modules, "ollama", SimpleNamespace(Client=FakeClient))
    return seen


def test_a_completion_is_asked_for_in_bounded_form(monkeypatch):
    """This is the fix for the slowest bug in the repo's history, and it never
    looked like a bug: every answer was correct, `/health` was green, and a full
    end-to-end pass took twenty-five minutes because the model was asked for an
    unbounded reply and abandoned at the 60-second budget every single time. The
    measurement was 667 reasoning tokens at 0.52 tokens/second for a one-sentence
    answer. Nothing failed. It was just never the model answering."""
    seen = fake_ollama(monkeypatch, {})
    from assistant.adapters import COMPLETION_TOKEN_CAP, ollama_generate

    out = ollama_generate("how long do refunds take", host="http://ollama:11434", model="m")
    assert out == "five business days"
    assert seen["think"] is False, "a reasoning model spends the whole budget deliberating"
    assert seen["options"]["num_predict"] == COMPLETION_TOKEN_CAP, (
        "an unbounded generation is a request whose duration the model decides"
    )


def test_the_stream_is_bounded_the_same_way(monkeypatch):
    """Sharper here than in the batch path: a client watching SSE would sit
    through the deliberation before the first word of the answer, and a stream
    whose first chunk is minutes away is not a stream."""
    seen = fake_ollama(monkeypatch, {})
    from assistant.adapters import COMPLETION_TOKEN_CAP, ollama_stream

    assert "".join(ollama_stream("q", host="http://ollama:11434", model="m")) == "five business days"
    assert seen["think"] is False
    assert seen["options"]["num_predict"] == COMPLETION_TOKEN_CAP


def test_an_upgrade_over_an_older_table_still_replays(tmp_path):
    """The bug this closes cost an end-to-end run: `CREATE TABLE IF NOT EXISTS`
    does nothing when the table exists, including when it exists with the wrong
    shape. A volume written by the build that only stored keys kept its
    two-column table, the new code's `UPDATE ... SET result` raised `no such
    column: result`, and it raised on the RETRY path — the health check was
    green, every read worked, and the first client to time out and ask again got
    a 500 for its trouble.

    This is why the schema is compared to the database rather than assumed: the
    only honest test of a migration is one that starts from the old schema."""
    db = tmp_path / "assistant.db"
    old = sqlite3.connect(db)
    old.execute(
        "CREATE TABLE idempotency_keys ("
        "  key TEXT PRIMARY KEY,"
        "  created_at TEXT NOT NULL DEFAULT (datetime('now'))"
        ")"
    )
    old.execute("INSERT INTO idempotency_keys (key) VALUES ('written-by-the-old-build')")
    old.commit()
    old.close()

    store = IdempotencyStore(str(db))
    result, replayed = store.run("batch-upgrade", lambda: {"ingested": 1})
    assert (result, replayed) == ({"ingested": 1}, False)
    assert store.run("batch-upgrade", lambda: {"ingested": 1}) == ({"ingested": 1}, True), (
        "the replay has to carry the original answer, which is what needs the column"
    )
    # The rows from before the upgrade survive it: a migration that protects the
    # new path by dropping the table would un-protect every key already claimed.
    assert store.run("written-by-the-old-build", lambda: {"ingested": 99})[1] is True


def test_a_retried_delete_is_acknowledged_not_reapplied():
    c = TestClient(create_app(Settings()))
    c.post("/ingest", json=DOC)
    headers = {"Idempotency-Key": "forget-1"}
    first = c.request("DELETE", "/corpus/r.md", headers=headers).json()
    replay = c.request("DELETE", "/corpus/r.md", headers=headers).json()
    assert first["deleted"] == 1
    assert replay["deleted"] == 1 and replay["replayed"] is True, (
        "the answer is the original one, and no second delete happened"
    )


# --- the outbox: irreversible intent, written down first ------------------------


def failing_send(*_args, **_kwargs):
    raise ConnectionError("telegram unreachable")


def crashing_send(*_args, **_kwargs):
    raise KeyboardInterrupt("the process was killed mid-send")


def recorded(fn, outbox: Outbox, request_id: str = "req-1"):
    """The send_telegram tool with `fn` for a body, wrapped by the outbox."""
    registry = dict(REGISTRY)
    registry["send_telegram"] = rewrap(registry["send_telegram"], fn)
    return recorded_registry(registry, outbox, "alice", request_id)["send_telegram"].fn


def test_the_intent_is_durable_before_the_call_happens():
    """The gap this closes: a crash between "the API accepted it" and "we wrote
    the row" leaves a message that went out and nothing in the system that
    remembers. The row is committed FIRST, so the worst case is a false alarm
    somebody can close rather than an effect nobody can account for."""
    outbox = Outbox()
    seen: list[str] = []

    def send(chat_id: str, message: str) -> dict:
        seen.append(str(outbox.pending()[0].status))
        return {"sent": True}

    recorded(send, outbox)(chat_id="ops", message="the site is down")
    assert seen == [PENDING], "the row existed while the call was in flight"
    assert [e.status for e in outbox.entries("alice")] == [SENT]


def test_a_process_that_dies_mid_send_leaves_a_pending_row():
    """Not an exception the tool can catch — a kill. `pending` is the honest
    state: we started something irreversible and never learned how it ended.
    That is a question for a human, which is strictly better than silence."""
    outbox = Outbox()
    with pytest.raises(KeyboardInterrupt):
        recorded(crashing_send, outbox)(chat_id="ops", message="hi")
    assert [e.status for e in outbox.pending()] == [PENDING]


def test_a_failed_send_is_written_down_as_failed():
    """Without this the row stays pending forever and reconciliation cannot tell
    "crashed mid-send" from "the API said no" — which are opposite answers to
    the only question being asked."""
    outbox = Outbox()
    with pytest.raises(ConnectionError):
        recorded(failing_send, outbox)(chat_id="ops", message="hi")
    assert [e.status for e in outbox.entries("alice")] == [FAILED]
    assert outbox.pending() == [], "a known failure is not an open question"


def test_a_read_only_tool_gets_no_outbox_row():
    """An envelope for a search is bookkeeping nobody will ever read."""
    outbox = Outbox()
    wrapped = recorded_registry(dict(REGISTRY), outbox, "alice", "req-1")
    wrapped["read_news"].fn()
    assert outbox.entries() == []


def test_the_same_call_twice_in_one_request_is_refused_not_sent_twice():
    """The last line of defence, and the only one holding the actual arguments.
    A retry that got past every layer above stops here."""
    outbox = Outbox()
    sends: list[str] = []
    send = recorded(lambda chat_id, message: sends.append(message) or {"sent": True},
                    outbox)
    send(chat_id="ops", message="the site is down")
    again = send(chat_id="ops", message="the site is down")
    assert len(sends) == 1
    assert "already recorded" in again["error"]


def test_a_deliberate_second_send_in_a_new_request_goes_through():
    """`request_id` is part of the key on purpose: two deliberate sends of the
    same message are two requests, and both should happen. A dedupe that cannot
    tell "retry" from "again" is a dedupe that loses messages."""
    outbox = Outbox()
    sends: list[str] = []

    def send(chat_id: str, message: str) -> dict:
        sends.append(message)
        return {"sent": True}

    recorded(send, outbox, "req-1")(chat_id="ops", message="ping")
    recorded(send, outbox, "req-2")(chat_id="ops", message="ping")
    assert len(sends) == 2


def test_an_approved_send_shows_up_in_the_outbox_over_http():
    c = TestClient(create_app(Settings()))
    approve(c, paused_call(c))
    c.post("/ask", json=SEND)
    body = c.get("/outbox").json()
    assert [e["tool"] for e in body["effects"]] == ["send_telegram"]
    assert body["effects"][0]["status"] == SENT
    assert body["pending"] == 0
    assert body["effects"][0]["request_id"], "an effect is traceable to its request"


# --- deadlines and callers who left ---------------------------------------------


def test_a_request_that_blows_its_deadline_gets_504():
    """A gateway timeout is an alert: the service was too slow and somebody
    should look at it."""
    c = TestClient(create_app(Settings(request_deadline=0.0)))
    response = c.post("/ask", json={"question": "how long do refunds take"})
    assert response.status_code == 504
    assert response.json()["detail"] == "deadline exceeded"


def test_a_caller_who_left_gets_499_and_not_an_alert():
    """499 is nginx's "client closed request". Nobody is there to receive it,
    and paging on it means paging every time a user closes a tab."""
    app = create_app(Settings())
    app.state.assistant.screen = lambda text: (_ for _ in ()).throw(
        deadline.Expired("caller disconnected")
    )
    c = TestClient(app)
    response = c.post("/ask", json={"question": "anything"})
    assert response.status_code == 499


def test_an_unbounded_request_is_still_the_default():
    """The fast tier drives a real model in the integration lane, where a
    deadline would be a flake generator. Off unless configured."""
    c = TestClient(create_app(Settings()))
    assert c.post("/ask", json={"question": "hello"}).status_code == 200


def test_a_stream_stops_early_when_nobody_is_listening():
    """Per FRAME, because that is the only place a long generation can be
    stopped at all. Under load this is the failure that compounds: tokens
    generated for callers who left are what slow down the callers who stayed."""
    app = create_app(Settings())
    a = app.state.assistant
    frames: list[str] = []
    gone = {"yet": False}

    def endless(goal, contexts, state, memories=None):
        for i in range(1000):
            yield f"word{i} "

    a.stream_compose = endless
    with deadline.budget(None, cancelled=lambda: gone["yet"]):
        for frame in a.ask_stream("tell me everything"):
            frames.append(frame)
            if len(frames) >= 3:
                gone["yet"] = True
    assert len(frames) < 1000, "the stream stopped when the caller did"
    root = [s for s in a.rec.spans() if s.name == "assistant.pipeline"][-1]
    assert root.attributes["request.abandoned"] == "caller disconnected", (
        "and the trace says why, so the short answer is not a mystery"
    )
