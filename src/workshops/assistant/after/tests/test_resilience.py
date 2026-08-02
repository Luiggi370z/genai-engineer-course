"""The reliability primitives, in isolation and in microseconds: injectable
sleep/clock means no test here ever actually waits."""

import time

import pytest

from assistant.resilience import ConcurrencyCap, Policy, TokenBucket, resilient


class Flaky:
    """Fails `failures` times, then succeeds."""

    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.calls = 0

    def __call__(self) -> str:
        self.calls += 1
        if self.calls <= self.failures:
            raise ConnectionError("transient")
        return "ok"


def test_a_transient_failure_is_retried_to_success():
    slept: list[float] = []
    fn = resilient(
        Flaky(failures=2), Policy(attempts=3, base_delay=0.2, timeout=None),
        sleep=slept.append, rng=lambda: 1.0,
    )
    assert fn() == "ok"
    assert slept == [0.2, 0.4], "exponential backoff between the three attempts"


def test_the_last_failure_propagates_when_attempts_run_out():
    fn = resilient(
        Flaky(failures=99), Policy(attempts=3, base_delay=0, timeout=None),
        sleep=lambda s: None,
    )
    with pytest.raises(ConnectionError):
        fn()


def test_backoff_is_capped_and_jittered():
    slept: list[float] = []
    fn = resilient(
        Flaky(failures=3), Policy(attempts=4, base_delay=1.0, max_delay=1.5, timeout=None),
        sleep=slept.append, rng=lambda: 0.5,
    )
    fn()
    # ceilings 1.0, 2.0->1.5(cap), 4.0->1.5(cap); jitter halves each
    assert slept == [0.5, 0.75, 0.75]


def test_a_call_that_overruns_its_timeout_raises():
    def slow() -> None:
        time.sleep(0.5)

    fn = resilient(slow, Policy(attempts=1, timeout=0.05))
    with pytest.raises(TimeoutError):
        fn()


def test_a_timeout_returns_promptly_instead_of_waiting_for_the_abandoned_call():
    """Regression, caught live: ThreadPoolExecutor as a context manager shuts down
    with wait=True, so the 'timed out' call still blocked until the stuck call
    finished — a 60s budget held /ask hostage for half an hour. The timeout must
    RETURN at the deadline; the overrun call is abandoned on its worker thread."""

    def stuck() -> None:
        time.sleep(1.5)  # far past the timeout — the caller must not wait this out

    fn = resilient(stuck, Policy(attempts=1, timeout=0.05))
    started = time.monotonic()
    with pytest.raises(TimeoutError):
        fn()
    elapsed = time.monotonic() - started
    assert elapsed < 1.0, f"timeout waited {elapsed:.2f}s for the abandoned call"


def test_the_bucket_allows_the_burst_then_refuses():
    now = {"t": 0.0}
    bucket = TokenBucket(rate=1.0, burst=2.0, clock=lambda: now["t"])
    assert bucket.take() and bucket.take()
    assert not bucket.take(), "burst exhausted, no time has passed"


def test_the_bucket_refills_with_time():
    now = {"t": 0.0}
    bucket = TokenBucket(rate=2.0, burst=2.0, clock=lambda: now["t"])
    bucket.take(), bucket.take()
    now["t"] = 0.5  # 0.5s * 2/s = 1 token back
    assert bucket.take()
    assert not bucket.take()


def test_the_cap_admits_up_to_the_limit_and_sheds_beyond_it():
    cap = ConcurrencyCap(limit=2)
    assert cap.enter() and cap.enter()
    assert not cap.enter(), "third concurrent request is shed"
    cap.leave()
    assert cap.enter(), "a slot freed is a slot usable"
    assert cap.active == 2
