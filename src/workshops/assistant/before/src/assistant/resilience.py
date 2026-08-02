"""Reliability primitives — stdlib only, injectable clocks, no magic.

Three small pieces the service composes around its network adapters:

- resilient(fn, policy)  : retries with exponential backoff + full jitter, and a
                           per-call timeout enforced from a worker thread
- TokenBucket            : the classic rate limiter — capacity is the burst, the
                           refill rate is the sustained requests-per-second
- ConcurrencyCap         : an admission counter — over the cap means REJECT, not
                           queue, because a queued request still holds the caller

Everything takes an injectable clock/sleep so the tests run in microseconds and
never actually wait.
"""
from __future__ import annotations

import random
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass, field
from threading import Lock
from typing import Any


@dataclass(frozen=True)
class Policy:
    """How hard to try before giving up. attempts counts the FIRST call too."""

    attempts: int = 3
    base_delay: float = 0.2
    max_delay: float = 5.0
    timeout: float | None = 10.0


DEFAULT_POLICY = Policy()


def resilient(
    fn: Callable[..., Any],
    policy: Policy = DEFAULT_POLICY,
    *,
    sleep: Callable[[float], None] = time.sleep,
    rng: Callable[[], float] = random.random,
) -> Callable[..., Any]:
    """Wrap a callable in retries + backoff + timeout. The LAST failure always
    propagates — resilience means trying again, not pretending it worked.

    Backoff is exponential with FULL jitter (delay drawn uniformly from
    [0, base * 2^attempt]) — the variant that empties a thundering herd fastest.
    The timeout runs the call on a worker thread; a call that overruns is
    abandoned there (Python cannot kill it) and reported as TimeoutError here."""

    def timed(*args: Any, **kwargs: Any) -> Any:
        if policy.timeout is None:
            return fn(*args, **kwargs)
        # NOT a `with` block: the context manager's __exit__ is shutdown(wait=True),
        # which would block right here until the abandoned call finished — turning
        # the timeout into a lie. (Caught live: a stalled model generation held
        # /ask hostage for half an hour past its 60s budget.) shutdown(wait=False)
        # lets the worker thread die with the overrun call still on it.
        pool = ThreadPoolExecutor(max_workers=1)
        try:
            future = pool.submit(fn, *args, **kwargs)
            try:
                return future.result(timeout=policy.timeout)
            except FutureTimeout:
                raise TimeoutError(
                    f"{getattr(fn, '__name__', 'call')} exceeded {policy.timeout}s"
                ) from None
        finally:
            pool.shutdown(wait=False, cancel_futures=True)

    def wrapped(*args: Any, **kwargs: Any) -> Any:
        for attempt in range(policy.attempts):
            try:
                return timed(*args, **kwargs)
            except Exception:
                if attempt == policy.attempts - 1:
                    raise
                ceiling = min(policy.max_delay, policy.base_delay * (2**attempt))
                sleep(ceiling * rng())
        raise AssertionError("unreachable")  # pragma: no cover

    return wrapped


@dataclass
class TokenBucket:
    """rate tokens/second refill, burst capacity. take() never blocks — a caller
    that finds the bucket empty gets False and should answer 429."""

    rate: float
    burst: float
    clock: Callable[[], float] = time.monotonic
    _tokens: float = field(init=False)
    _last: float = field(init=False)
    _lock: Lock = field(init=False, default_factory=Lock)

    def __post_init__(self) -> None:
        self._tokens = self.burst
        self._last = self.clock()

    def take(self, n: float = 1.0) -> bool:
        with self._lock:
            now = self.clock()
            self._tokens = min(self.burst, self._tokens + (now - self._last) * self.rate)
            self._last = now
            if self._tokens >= n:
                self._tokens -= n
                return True
            return False


@dataclass
class ConcurrencyCap:
    """Admission control: at most `limit` requests in flight. enter() is
    non-blocking — beyond the cap the service should shed load (503), because a
    request parked in a queue still ties up its caller's budget."""

    limit: int
    _active: int = field(init=False, default=0)
    _lock: Lock = field(init=False, default_factory=Lock)

    @property
    def active(self) -> int:
        return self._active

    def enter(self) -> bool:
        with self._lock:
            if self._active >= self.limit:
                return False
            self._active += 1
            return True

    def leave(self) -> None:
        with self._lock:
            self._active = max(0, self._active - 1)
