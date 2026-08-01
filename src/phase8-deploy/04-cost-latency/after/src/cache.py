"""Rungs 2 and 3 of the ladder: exact caching, then semantic caching.

The two are not variations of one idea, and the difference is the point of this
module. An exact cache **cannot** change an answer: same key, same stored reply. A
semantic cache can, because it decides that a *different* question is close enough
to reuse — and that decision is a quality trade-off with a number attached to it.

So the threshold is not a tuning constant. It is a product decision you sweep and
defend, exactly like the judge threshold in Phase 3.
"""
from __future__ import annotations

import hashlib
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

Embedder = Callable[[str], Sequence[float]]
Clock = Callable[[], float]


def cache_key(question: str, context: str, model: str, tier: str = "default") -> str:
    """A key over *everything that changes the answer*.

    The classic production bug is keying on the question alone. Then the document
    behind it is re-indexed, the answer should change, and the cache confidently
    serves last week's. If a field can change the reply, it belongs in the key.
    """
    parts = "\u0000".join([question.strip().lower(), context, model, tier])
    return hashlib.sha256(parts.encode("utf-8")).hexdigest()


@dataclass
class Entry:
    answer: str
    stored_at: float
    vector: Sequence[float] | None = None
    question: str = ""


@dataclass
class ExactCache:
    """Same key, same answer, until the TTL runs out.

    The TTL is the only correctness knob here, and it is a statement about how
    stale an answer is allowed to be — not a performance setting.
    """

    ttl_s: float = 300.0
    clock: Clock = time.monotonic
    entries: dict[str, Entry] = field(default_factory=dict)
    hits: int = 0
    misses: int = 0

    def get(self, key: str) -> str | None:
        entry = self.entries.get(key)
        if entry is None or self.clock() - entry.stored_at > self.ttl_s:
            if entry is not None:
                del self.entries[key]  # expired: drop it rather than re-check forever
            self.misses += 1
            return None
        self.hits += 1
        return entry.answer

    def put(self, key: str, answer: str) -> None:
        self.entries[key] = Entry(answer=answer, stored_at=self.clock())

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """Plain cosine similarity. No numpy needed at this size."""
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


@dataclass
class SemanticCache:
    """Reuse the answer to a *similar* question, above a similarity threshold.

    The embedder is injected: a scripted one offline, fastembed in the integration
    tier. Every honest test of this class is really a test of the threshold.
    """

    embed: Embedder
    threshold: float = 0.95
    ttl_s: float = 300.0
    clock: Clock = time.monotonic
    entries: list[Entry] = field(default_factory=list)
    hits: int = 0
    misses: int = 0

    def _live(self) -> list[Entry]:
        now = self.clock()
        self.entries = [e for e in self.entries if now - e.stored_at <= self.ttl_s]
        return self.entries

    def nearest(self, question: str) -> tuple[Entry, float] | None:
        """The closest live entry and its score, whatever the threshold says.

        Exposed separately so you can sweep thresholds over recorded traffic
        without re-embedding anything.
        """
        vector = self.embed(question)
        scored = [
            (entry, cosine(vector, entry.vector))
            for entry in self._live()
            if entry.vector is not None
        ]
        return max(scored, key=lambda pair: pair[1]) if scored else None

    def get(self, question: str) -> str | None:
        best = self.nearest(question)
        if best is None or best[1] < self.threshold:
            self.misses += 1
            return None
        self.hits += 1
        return best[0].answer

    def put(self, question: str, answer: str) -> None:
        self.entries.append(
            Entry(
                answer=answer,
                stored_at=self.clock(),
                vector=self.embed(question),
                question=question,
            )
        )

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0


@dataclass(frozen=True)
class SweepRow:
    threshold: float
    reuses: int  # how often the cache answered at all
    wrong_reuses: int  # ...and how often it was the wrong answer

    @property
    def precision(self) -> float:
        return (self.reuses - self.wrong_reuses) / self.reuses if self.reuses else 1.0


def sweep(
    embed: Embedder,
    stored: Sequence[tuple[str, str]],
    probes: Sequence[tuple[str, bool]],
    thresholds: Sequence[float],
) -> list[SweepRow]:
    """Pick a threshold with evidence instead of a shrug.

    `stored` is (question, answer) already in the cache. `probes` is
    (question, should_reuse) — your labels, saying whether reusing a stored answer
    for that question would actually be correct.

    A high threshold caches almost nothing safely; a low one caches a lot and
    starts answering the wrong question. There is no default that is right for
    every corpus, which is exactly why this function exists rather than a constant.
    """
    rows: list[SweepRow] = []
    for threshold in thresholds:
        cache = SemanticCache(embed=embed, threshold=threshold, ttl_s=float("inf"))
        for question, answer in stored:
            cache.put(question, answer)
        reuses = wrong = 0
        for question, should_reuse in probes:
            if cache.get(question) is not None:
                reuses += 1
                if not should_reuse:
                    wrong += 1
        rows.append(SweepRow(threshold=threshold, reuses=reuses, wrong_reuses=wrong))
    return rows
