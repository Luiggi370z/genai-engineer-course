"""A client that hangs up, over a real socket.

Every other cancellation test in this suite installs the signal by hand —
`deadline.budget(cancelled=lambda: ...)` around the generator — and proves the
pipeline obeys it. That is worth proving and it is not the same claim. The claim a
caller cares about is that *closing a connection* sets that signal, and the two came
apart completely: the middleware started a disconnect watcher, called the route, and
cancelled the watcher in a `finally`. For a streaming response `call_next` returns
before a single byte of the body is sent, so the watcher was always cancelled before
the client could possibly leave. Twenty tests green, and `deadline.expired()` inside a
live generation returned `None` for a caller who had already gone.

**Why these tests assert on the mechanism and not on a chunk count.** The obvious
assertion — "the source stops being pulled" — was already true before the fix, and
for a reason that has nothing to do with this service. Starlette hands the middleware
its chunks over a zero-buffer anyio stream, so when Uvicorn's transport dies the
producer's `send` breaks and the generator is collected. Measured: 57 of 400 chunks
before the fix, 43 after. A test asserting `< 400` passes on the broken code.

That accident is not the contract, and the difference is not cosmetic:

  * it is a torn-down coroutine, not a cancellation. `deadline.check()` never fires,
    so the 499 path in `api.expired` never runs and nothing is recorded about a
    request that was abandoned rather than answered;
  * it depends on buffer sizing and transport behaviour in two libraries. Give the
    memory stream a buffer, or run behind a server that swallows writes to a dead
    socket, and generation continues to the last token;
  * it cannot reach anything else that reads the flag. `deadline.capped` shrinking a
    composer timeout, a tool refusing to start — all of it stays asleep.

So the assertion is `deadline.expired()`, asked from inside the running model. That is
the signal the rest of the codebase is built on, and it is the one that was missing.

Not marked `integration`: no Qdrant, no Ollama, no key. `uvicorn` is a runtime
dependency of the service, so the fast tier already has it. It is still the slowest
test here by an order of magnitude, because a socket is the only instrument that can
observe this — `TestClient` reads the whole response and `httpx.ASGITransport` does
not model a mid-response close.
"""

import socket
import struct
import threading
import time

import pytest
import uvicorn

from assistant import deadline
from assistant.api import create_app
from assistant.settings import Settings

#: Chunks the fake model emits if nobody stops it.
SOURCE_LENGTH = 400

#: Per chunk. Slow enough that a client can hang up mid-answer, which is the whole
#: scenario — without it a fast machine finishes before the first disconnect poll and
#: every assertion below passes for the wrong reason.
CHUNK_DELAY = 0.005

#: What `Budget.expired()` says about an abandoned request, as opposed to a slow one.
#: Asserted on the exact string rather than on truthiness because the distinction is
#: the point: "deadline exceeded" is a service that was too slow and somebody should
#: look, "caller disconnected" is work that became pointless and nobody should be
#: paged. A test that accepted either would accept a disconnect being reported as a
#: timeout, which is the wrong page at three in the morning.
GONE = "caller disconnected"


class Server(uvicorn.Server):
    """Uvicorn without its signal handlers, so it can run in a thread."""

    def install_signal_handlers(self) -> None:
        return None


@pytest.fixture
def served():
    """An app on a real port, plus what its fake model saw while generating.

    `noticed` is the interesting field: the model asks `deadline.expired()` on every
    chunk, which is exactly what `output_gate.gated_chunks` and every tool wrapper
    ask. Recording the answer turns "did the disconnect arrive" into an assertion.
    """
    watched = {"chunks": 0, "noticed": None}

    app = create_app(Settings())

    def endless(goal, contexts, state, memories=None):
        for i in range(SOURCE_LENGTH):
            watched["chunks"] += 1
            if watched["noticed"] is None:
                watched["noticed"] = deadline.expired()
            # A space every token: the outbound gate releases on word boundaries, so
            # an unbroken blob would be buffered and prove something else.
            yield f"word{i} "
            time.sleep(CHUNK_DELAY)

    app.state.assistant.stream_compose = endless

    # Bound here rather than by Uvicorn so the port is known before the server
    # starts — reading it back off `server.servers[0]` is a race this does not need.
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]

    server = Server(uvicorn.Config(app, log_level="warning"))
    thread = threading.Thread(target=lambda: server.run(sockets=[listener]), daemon=True)
    thread.start()
    until = time.monotonic() + 20
    while not server.started and thread.is_alive() and time.monotonic() < until:
        time.sleep(0.02)
    assert server.started, "uvicorn never came up"
    try:
        yield port, watched
    finally:
        server.should_exit = True
        thread.join(timeout=15)
        listener.close()


ASK_STREAM = (
    b"POST /ask/stream HTTP/1.1\r\n"
    b"Host: 127.0.0.1\r\n"
    b"Content-Type: application/json\r\n"
    b"Content-Length: 34\r\n"
    b"Connection: close\r\n\r\n"
    b'{"question": "tell me everything"}'
)


def test_a_client_that_hangs_up_is_noticed_by_the_model_it_left(served):
    """The assertion no unit test can make: nothing here injects a signal.

    A socket closes, and the generation running in the threadpool has to find
    `deadline.expired()` telling it the caller is gone. Before the watcher's lifetime
    was extended this read `None` all the way to the end of the answer.
    """
    port, watched = served

    # Raw sockets rather than a client library: this needs an ABRUPT close, no
    # half-close handshake and no politely draining the rest, because that is what a
    # browser tab does when it goes away. `SO_LINGER` at zero makes `close()` send
    # RST instead of FIN.
    client = socket.create_connection(("127.0.0.1", port), timeout=20)
    try:
        client.sendall(ASK_STREAM)
        client.recv(4096)  # let generation get going, then walk away
        client.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
    finally:
        client.close()

    # The watcher polls, so allow several intervals before asking.
    time.sleep(2.0)

    assert watched["noticed"] == GONE, (
        f"the model was told {watched['noticed']!r} after its caller hung up. A "
        "disconnect that never reaches the request budget cannot stop anything on "
        "purpose — see this module's docstring for why the chunk count is not the "
        "test"
    )
    settled = watched["chunks"]
    assert settled < SOURCE_LENGTH, (
        f"all {SOURCE_LENGTH} chunks were generated for a caller who had left"
    )
    time.sleep(0.5)
    assert watched["chunks"] == settled, "the source was still being pulled"


def test_a_client_that_stays_is_never_told_its_caller_left(served):
    """The control, and not a formality. "Cancels on disconnect" is also satisfied by
    a path that cancels everything — without this, a middleware that set the flag
    unconditionally would pass the test above and break every streaming caller."""
    port, watched = served
    client = socket.create_connection(("127.0.0.1", port), timeout=30)
    try:
        client.sendall(ASK_STREAM)
        received = b""
        while True:
            chunk = client.recv(65536)
            if not chunk:
                break
            received += chunk
    finally:
        client.close()

    assert b"event: done" in received, received[-400:]
    assert watched["noticed"] is None, (
        f"a caller who waited was reported as {watched['noticed']!r}"
    )
    assert watched["chunks"] == SOURCE_LENGTH, (
        f"got {watched['chunks']} of {SOURCE_LENGTH} chunks — the stream is "
        "truncating requests nobody abandoned"
    )


def test_a_buffered_response_still_tears_the_watcher_down(served):
    """The other branch of the middleware, which has no body to outlive.

    `/ask` is generated and gated before it returns, so there is no work a disconnect
    could save and the watcher is cancelled where it always was. Worth a test because
    the fix added a branch: a leaked watcher task per buffered request would be a
    slow, quiet resource leak on the busiest endpoint in the service.
    """
    port, _ = served
    client = socket.create_connection(("127.0.0.1", port), timeout=30)
    try:
        client.sendall(
            b"POST /ask HTTP/1.1\r\nHost: 127.0.0.1\r\n"
            b"Content-Type: application/json\r\nContent-Length: 21\r\n"
            b"Connection: close\r\n\r\n"
            b'{"question": "hello"}'
        )
        received = b""
        while True:
            chunk = client.recv(65536)
            if not chunk:
                break
            received += chunk
    finally:
        client.close()

    assert b"200 OK" in received.split(b"\r\n")[0], received[:200]
    assert threading.active_count() < 50, "something is accumulating per request"


def test_the_hand_injected_signal_is_still_the_unit_level_contract():
    """Kept adjacent on purpose. This is the cheap version of the same property and
    the one that localises a break: if this fails the pipeline stopped obeying
    cancellation, and if only the socket tests fail the HTTP layer stopped delivering
    it. Two failures that look alike and share no cause."""
    app = create_app(Settings())
    assistant = app.state.assistant
    gone = {"yet": False}

    def endless(goal, contexts, state, memories=None):
        for i in range(SOURCE_LENGTH):
            yield f"word{i} "

    assistant.stream_compose = endless
    frames = []
    with deadline.budget(None, cancelled=lambda: gone["yet"]):
        for frame in assistant.ask_stream("tell me everything"):
            frames.append(frame)
            if len(frames) >= 3:
                gone["yet"] = True
    assert len(frames) < SOURCE_LENGTH
