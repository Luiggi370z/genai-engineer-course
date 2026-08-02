"""Degraded operation — real adapters fail soft, never hard.

A capstone that 500s because Qdrant restarted has not learned the operate
lesson. Every network adapter is wrapped twice: `resilient` retries transient
failures, and if the call still fails the OFFLINE default answers instead —
with the degradation reported on /health so an operator can see it. Retry
budgets differ by adapter: a vector search should fail fast (the standby is
right there); a model completion is worth waiting for.
"""
from __future__ import annotations

from collections.abc import Callable, Iterator
from queue import Empty, Queue
from threading import Thread
from typing import Any

from assistant import auth
from assistant.agent import Step
from assistant.composers import Composer, StreamComposer, offline_compose, word_stream
from assistant.resilience import Policy, resilient

RAG_POLICY = Policy(attempts=3, base_delay=0.2, timeout=10.0)
COMPOSE_POLICY = Policy(attempts=2, base_delay=0.2, timeout=60.0)


class FallbackRag:
    """Primary RAG with retries, offline BM25 as the warm standby. Ingest is
    MIRRORED into the standby up front — a fallback with an empty corpus at
    query time would be an abstention generator, not a fallback."""

    def __init__(
        self,
        primary: Any,
        fallback: Any,
        report: Callable[[str, str], None],
        policy: Policy = RAG_POLICY,
    ) -> None:
        self.primary = primary
        self.fallback = fallback
        self._report = report
        self._add = resilient(primary.add, policy)
        self._search = resilient(primary.search, policy)

    def add(self, docs: list[str], tenant: str = auth.ANONYMOUS) -> int:
        self.fallback.add(docs, tenant=tenant)
        try:
            return self._add(docs, tenant=tenant)
        except Exception as exc:
            self._report("rag", f"ingest fell back to in-memory: {exc}")
            return len(docs)

    def search(self, query: str, k: int = 3, tenant: str = auth.ANONYMOUS) -> list[str]:
        try:
            return self._search(query, k, tenant=tenant)
        except Exception as exc:
            self._report("rag", f"search fell back to in-memory: {exc}")
            return self.fallback.search(query, k, tenant=tenant)


def fallback_composer(
    primary: Composer,
    report: Callable[[str, str], None],
    policy: Policy = COMPOSE_POLICY,
) -> Composer:
    """Model-tier composition with retries; the offline stitcher answers when the
    model stays down. Degraded prose beats a 500 — the evidence is already here."""
    guarded = resilient(primary, policy)

    def compose(goal: str, contexts: list[str], state: list[tuple[Step, Any]]) -> str:
        try:
            return guarded(goal, contexts, state)
        except Exception as exc:
            report("brain", f"composition fell back to offline: {exc}")
            return offline_compose(goal, contexts, state)

    return compose


def fallback_stream(
    primary: StreamComposer,
    report: Callable[[str, str], None],
    timeout: float | None = COMPOSE_POLICY.timeout,
) -> StreamComposer:
    """Streaming with a fallback, bounded in TIME as well as guarded on errors.

    The batch composer gets its timeout from `resilient`; a generator cannot,
    because the slowness happens between yields — so the primary is drained on a
    worker thread and each chunk must arrive within `timeout`. A model that dies
    or stalls BEFORE the first chunk falls back to the offline answer; one that
    stalls MID-stream truncates (those chunks are already on the wire). Either
    way the degradation is reported, never absorbed. (Caught live: a thinking
    model spent minutes reasoning before its first token, and the unbounded
    stream held /ask/stream hostage the whole time.)"""

    def stream(
        goal: str, contexts: list[str], state: list[tuple[Step, Any]]
    ) -> Iterator[str]:
        frames: Queue = Queue()

        def drain() -> None:
            try:
                for chunk in primary(goal, contexts, state):
                    frames.put(("chunk", chunk))
                frames.put(("end", None))
            except Exception as exc:  # noqa: BLE001 — the seam exists to catch anything
                frames.put(("error", exc))

        Thread(target=drain, daemon=True).start()  # abandoned on timeout, like resilient
        yielded = False
        while True:
            try:
                kind, payload = frames.get(timeout=timeout)
            except Empty:
                report("brain", f"stream produced no chunk within {timeout}s")
                if not yielded:
                    yield from word_stream(offline_compose)(goal, contexts, state)
                return
            if kind == "chunk":
                yielded = True
                yield payload
            elif kind == "error":
                report("brain", f"stream fell back to offline: {payload}")
                if not yielded:
                    yield from word_stream(offline_compose)(goal, contexts, state)
                return
            else:
                return

    return stream
