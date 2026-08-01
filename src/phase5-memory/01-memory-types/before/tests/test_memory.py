"""Offline, deterministic tests for the memory store.

Everything here runs with the hash embedder: no model, no network, same result every
time. The one claim that genuinely needs real embeddings — paraphrase recall — is
marked `integration` and lives at the bottom.
"""

from __future__ import annotations

import pytest

from src.memory import DAY_SECONDS, VectorMemory, classify, hash_embedder, report

NOW = 1_800_000_000.0


@pytest.fixture
def store() -> VectorMemory:
    return VectorMemory(hash_embedder())


def test_a_written_fact_is_recallable_with_its_source(store: VectorMemory) -> None:
    store.write("semantic", "Lu works in UTC-5", source="turn-3", now=NOW)
    hits = store.recall("semantic", "what timezone?", now=NOW)
    assert [h.text for h in hits] == ["Lu works in UTC-5"]
    assert hits[0].source == "turn-3"


def test_kinds_are_isolated(store: VectorMemory) -> None:
    """A procedural recipe must never be the answer to a question about the user."""
    store.write("procedural", "Retry the calendar tool once on a 429", source="run-2", now=NOW)
    store.write("semantic", "Lu works in UTC-5", source="turn-3", now=NOW)
    semantic = store.recall("semantic", "calendar tool retry", now=NOW)
    procedural = store.recall("procedural", "UTC-5 timezone", now=NOW)
    assert [h.kind for h in semantic] == ["semantic"]
    assert [h.kind for h in procedural] == ["procedural"]


def test_users_are_isolated(store: VectorMemory) -> None:
    store.write("semantic", "Lu works in UTC-5", source="turn-3", now=NOW)
    other = VectorMemory(hash_embedder(), user="someone-else", client=store.client)
    assert other.recall("semantic", "what timezone?", now=NOW) == []


def test_forget_removes_the_row_rather_than_lowering_its_rank(store: VectorMemory) -> None:
    stale = store.write("semantic", "Dana is my manager", source="turn-4", now=NOW)
    store.write("semantic", "Ravi is my manager", source="turn-91", now=NOW)
    store.forget(stale)
    remaining = [h.text for h in store.recall("semantic", "who is my manager", k=5, now=NOW)]
    assert remaining == ["Ravi is my manager"]


def test_an_expired_memory_stops_being_recallable(store: VectorMemory) -> None:
    store.write("semantic", "Dana is my manager", source="turn-4", ttl_days=30, now=NOW)
    assert store.recall("semantic", "who is my manager", now=NOW)
    later = NOW + 31 * DAY_SECONDS
    assert store.recall("semantic", "who is my manager", now=later) == []


def test_rows_without_an_expiry_survive_the_ttl_filter(store: VectorMemory) -> None:
    """The null-vs-range trap: a plain range filter drops every `expires_at: null` row."""
    store.write("semantic", "Lu works in UTC-5", source="turn-3", ttl_days=None, now=NOW)
    store.write("semantic", "Dana is my manager", source="turn-4", ttl_days=1, now=NOW)
    much_later = NOW + 400 * DAY_SECONDS
    assert [h.text for h in store.recall("semantic", "manager timezone", k=5, now=much_later)] == [
        "Lu works in UTC-5"
    ]


def test_forget_all_drops_one_namespace_and_leaves_the_others(store: VectorMemory) -> None:
    store.write("semantic", "Lu works in UTC-5", source="turn-3", now=NOW)
    store.write("semantic", "Dana is my manager", source="turn-4", now=NOW)
    store.write("procedural", "Retry once on a 429", source="run-2", now=NOW)
    assert store.forget_all("semantic") == 2
    assert store.recall("semantic", "anything", now=NOW) == []
    assert len(store.recall("procedural", "retry", now=NOW)) == 1


def test_a_memory_without_provenance_is_refused(store: VectorMemory) -> None:
    with pytest.raises(ValueError, match="source"):
        store.write("semantic", "something true", source="  ", now=NOW)


def test_expired_rows_stay_visible_to_the_report(store: VectorMemory) -> None:
    """Expiry hides a fact from recall; it must not hide it from the audit."""
    store.write("semantic", "Dana is my manager", source="turn-4", ttl_days=1, now=NOW)
    later = NOW + 2 * DAY_SECONDS
    assert store.recall("semantic", "manager", now=later) == []
    assert len(store.all("semantic")) == 1
    assert "expired=1" in report(store, now=later)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Retry the calendar tool once on a 429", "procedural"),
        ("The fetch failed when the URL had no scheme", "episodic"),
        ("Lu prefers meetings after 10:00", "semantic"),
        ("Draft the Q3 budget summary", "working"),
    ],
)
def test_classify_routes_a_claim_to_a_kind(text: str, expected: str) -> None:
    assert classify(text) == expected


@pytest.mark.integration
def test_real_embeddings_recall_a_paraphrase() -> None:
    """The claim the hash embedder cannot make: no shared words, same meaning."""
    from src.memory import fastembed_embedder

    store = VectorMemory(fastembed_embedder())
    store.write("semantic", "Lu is based in Lima, on Peruvian hours", source="turn-3", now=NOW)
    store.write("procedural", "Retry the calendar tool once on a 429", source="run-2", now=NOW)
    hits = store.recall("semantic", "which timezone should I schedule in?", k=1, now=NOW)
    assert hits and "Lima" in hits[0].text
