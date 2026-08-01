"""ONE contract suite, run against every implementation of `MemoryStore`.

Offline (`make test`) it runs against `FakeStore`: no model, no vendor, no network.
In the integration tier it runs the identical assertions against Mem0 and LangMem.

That is the deliverable of this lesson. Adapters come and go — these assertions are
what you own, and they are what makes "we could swap Mem0 out" a claim rather than a
hope. When a test fails for one adapter only, you have found a difference that would
otherwise have surfaced in production.
"""

from __future__ import annotations

import time

import pytest

from src.adapters import build_store
from src.store import MemoryStore

#: A moment far enough in the past that anything expiring a day later is long gone.
LONG_AGO = time.time() - 400 * 86_400

FAST_ADAPTERS = ["fake"]
RENTED_ADAPTERS = ["mem0", "langmem"]


@pytest.fixture(params=FAST_ADAPTERS)
def store(request: pytest.FixtureRequest) -> MemoryStore:
    return build_store(request.param)


@pytest.fixture(params=RENTED_ADAPTERS)
def rented(request: pytest.FixtureRequest) -> MemoryStore:
    pytest.importorskip(
        "mem0" if request.param == "mem0" else "langmem",
        reason="rented adapters live in the integration group",
    )
    return build_store(request.param)


# --------------------------------------------------------------- the contract
def contract_a_written_fact_is_recallable(store: MemoryStore) -> None:
    store.write("semantic", "Lu works in UTC-5", source="turn-3")
    hits = store.recall("semantic", "which timezone does Lu work in?")
    assert any("UTC-5" in hit.text for hit in hits)


def contract_provenance_survives_the_round_trip(store: MemoryStore) -> None:
    """A claim you cannot trace is a claim you cannot delete when it turns out wrong."""
    store.write("semantic", "Ravi is my manager", source="turn-91")
    hits = store.recall("semantic", "who is my manager")
    assert hits and hits[0].source == "turn-91"


def contract_a_blank_source_is_refused(store: MemoryStore) -> None:
    with pytest.raises(ValueError, match="source"):
        store.write("semantic", "something true", source="   ")


def contract_kinds_are_isolated(store: MemoryStore) -> None:
    store.write("procedural", "Retry the calendar tool once on a 429", source="run-2")
    hits = store.recall("semantic", "retry the calendar tool")
    assert all(hit.kind == "semantic" for hit in hits)
    assert not any("429" in hit.text for hit in hits)


def contract_forget_actually_forgets(store: MemoryStore) -> None:
    memory_id = store.write("semantic", "Dana is my manager", source="turn-4")
    store.forget(memory_id)
    assert not any("Dana" in hit.text for hit in store.recall("semantic", "who is my manager"))


def contract_an_expired_fact_is_not_recalled(store: MemoryStore) -> None:
    """Written long ago with a one-day life: every adapter must agree it is gone."""
    store.write("semantic", "The office wifi password is hunter2", source="turn-7",
                ttl_days=1, now=LONG_AGO)
    assert not any("hunter2" in hit.text for hit in store.recall("semantic", "wifi password"))


def contract_recall_respects_k(store: MemoryStore) -> None:
    for index in range(6):
        store.write("episodic", f"run {index} failed on a timeout", source=f"run-{index}")
    assert len(store.recall("episodic", "timeout failure", k=2)) <= 2


CONTRACT = [
    contract_a_written_fact_is_recallable,
    contract_provenance_survives_the_round_trip,
    contract_a_blank_source_is_refused,
    contract_kinds_are_isolated,
    contract_forget_actually_forgets,
    contract_an_expired_fact_is_not_recalled,
    contract_recall_respects_k,
]


@pytest.mark.parametrize("check", CONTRACT, ids=lambda fn: fn.__name__[len("contract_") :])
def test_contract_holds_offline(store: MemoryStore, check) -> None:
    check(store)


@pytest.mark.integration
@pytest.mark.parametrize("check", CONTRACT, ids=lambda fn: fn.__name__[len("contract_") :])
def test_contract_holds_for_rented_stores(rented: MemoryStore, check) -> None:
    """The same assertions, against Mem0 and LangMem. Needs Ollama for the Mem0 path."""
    check(rented)


# ------------------------------------------------- what the fake is allowed to be
def test_the_fake_satisfies_the_protocol_structurally() -> None:
    assert isinstance(build_store("fake"), MemoryStore)


def test_an_unknown_adapter_name_fails_loudly() -> None:
    with pytest.raises(ValueError, match="unknown store"):
        build_store("whatever-launched-last-week")


def test_writes_are_counted(store: MemoryStore) -> None:
    store.write("semantic", "Lu works in UTC-5", source="turn-3")
    store.write("procedural", "Retry once on a 429", source="run-2")
    assert store.count() == 2
    assert store.count("semantic") == 1
