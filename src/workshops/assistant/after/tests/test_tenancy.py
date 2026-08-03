"""Memory belongs to a person, and recall has to enforce that.

The shipped defect was quiet: one store for everyone, `user="me"`, with the real
caller written into a `source` label that `recall` never reads. Nothing looked
broken — alice got her own answers back — right up until bob asked a question
whose words happened to match one of her memories.

These tests are written against the leak rather than the fix, so they would fail
again if someone reintroduced a single shared store.
"""
import sqlite3

import pytest

from assistant.composers import ABSTAIN
from assistant.core import Assistant
from assistant.memory import AssistantMemory
from assistant.rag import Chunk
from assistant.service import build_assistant
from assistant.settings import Settings
from assistant.sqlite_memory import SqliteMemory
from assistant.tenancy import TenantMemory

ALICE_FACT = "I prefer to be called Lu and I work in the Lima timezone"
BOB_QUESTION = "what timezone should we use for the Lima call"


def in_memory() -> TenantMemory:
    return TenantMemory(lambda subject: AssistantMemory(user=subject))


def on_disk(tmp_path) -> TenantMemory:
    db = str(tmp_path / "memory.db")
    return TenantMemory(lambda subject: SqliteMemory(db, user=subject))


# --- the leak ------------------------------------------------------------------
@pytest.mark.parametrize("backend", ["memory", "sqlite"])
def test_one_persons_memory_never_surfaces_in_anothers_recall(backend, tmp_path):
    store = in_memory() if backend == "memory" else on_disk(tmp_path)
    store.remember(ALICE_FACT, source="user:alice", subject="alice")

    assert [row.text for row in store.recall("semantic", BOB_QUESTION, subject="alice")]
    assert store.recall("semantic", BOB_QUESTION, subject="bob") == []


@pytest.mark.parametrize("backend", ["memory", "sqlite"])
def test_each_subject_recalls_their_own_answer_to_the_same_question(backend, tmp_path):
    store = in_memory() if backend == "memory" else on_disk(tmp_path)
    store.remember("I prefer the window seat", source="user:alice", subject="alice")
    store.remember("I prefer the aisle seat", source="user:bob", subject="bob")

    def recalled(subject: str) -> str:
        return store.recall("semantic", "which seat do I prefer", subject=subject)[0].text

    assert "window" in recalled("alice")
    assert "aisle" in recalled("bob")


def test_the_partition_is_in_the_database_not_only_in_the_process(tmp_path):
    """A restart must not merge tenants. The rows carry the subject, so a fresh
    process reading the same file still answers only for the caller."""
    db = str(tmp_path / "memory.db")
    first = TenantMemory(lambda subject: SqliteMemory(db, user=subject))
    first.remember(ALICE_FACT, source="user:alice", subject="alice")

    rows = sqlite3.connect(db).execute("SELECT DISTINCT user FROM memories").fetchall()
    assert rows == [("alice",)]

    reborn = TenantMemory(lambda subject: SqliteMemory(db, user=subject))
    assert reborn.recall("semantic", BOB_QUESTION, subject="bob") == []
    assert reborn.recall("semantic", BOB_QUESTION, subject="alice")


def test_all_crosses_tenants_because_it_is_the_operator_view():
    store = in_memory()
    store.remember("I prefer the window seat", source="user:alice", subject="alice")
    store.remember("I prefer the aisle seat", source="user:bob", subject="bob")
    assert len(store.all("semantic")) == 2


def test_a_turn_not_worth_remembering_is_not_remembered():
    store = in_memory()
    assert store.remember("what time is it", source="user:alice", subject="alice") is None
    assert store.all() == []


# --- recall through the whole pipeline -----------------------------------------
def test_the_assistant_answers_from_a_fact_the_same_caller_stated_earlier():
    """The assertion is on the ANSWER, and that is the whole point of it.

    This test used to check `answer["memories"]` and passed while the assistant
    replied "I don't know" with `Lima` sitting in the response metadata beside
    it. Recall worked; nothing consumed it. A memory the caller cannot see in
    the answer is a memory the system does not have."""
    assistant = build_assistant(Settings())
    assistant.ask(ALICE_FACT, subject="alice")
    answer = assistant.ask("which timezone should we schedule in", subject="alice")
    assert "Lima" in answer["answer"]
    assert answer["grounding"] == "memory"


def test_the_assistant_does_not_answer_from_another_callers_fact():
    assistant = build_assistant(Settings())
    assistant.ask(ALICE_FACT, subject="alice")
    answer = assistant.ask("which timezone should we schedule in", subject="bob")
    assert answer["memories"] == []
    assert "Lima" not in answer["answer"]
    assert answer["grounding"] == "none"


def test_a_recalled_memory_is_never_passed_off_as_a_citation():
    """Personalisation must not become fabricated grounding: a memory can colour
    an answer, but only a retrieved document earns a citation.

    Load-bearing now that memory can answer on its own — the previous version of
    this test was satisfied by an assistant that abstained."""
    assistant = build_assistant(Settings())
    assistant.ask(ALICE_FACT, subject="alice")
    answer = assistant.ask("which timezone should we schedule in", subject="alice")
    assert answer["memories"]
    assert answer["citations"] == []
    # attributed to the person, not to a document that does not exist
    assert "told me" in answer["answer"].lower()


def test_a_memory_answer_says_so_rather_than_stating_it_as_fact():
    """"You told me earlier" and "Lima is your timezone" are different claims
    with different failure modes. The first is checkable by the person reading
    it; the second is the assistant vouching for something it never verified."""
    assistant = build_assistant(Settings())
    assistant.ask(ALICE_FACT, subject="alice")
    answer = assistant.ask("which timezone should we schedule in", subject="alice")
    assert answer["answer"].startswith("You told me earlier:")


def test_an_unrelated_memory_does_not_license_an_answer():
    """The negative half, and the one that keeps this from being a regression.

    Recall is greedy — it returns what it has about the caller. If any memory at
    all were enough to answer, knowing alice's timezone would turn every
    unanswerable question into an answer about Lima. That is worse than the
    abstention it replaced, because it is confident."""
    assistant = build_assistant(Settings())
    assistant.ask(ALICE_FACT, subject="alice")
    answer = assistant.ask("what is the refund policy", subject="alice")
    assert answer["answer"] == ABSTAIN
    assert answer["grounding"] == "none"


def test_a_document_answer_is_still_grounded_in_documents():
    """Memory does not outrank evidence: with a real document in front of it the
    assistant answers from the document and cites it."""
    assistant = build_assistant(Settings())
    assistant.ask(ALICE_FACT, subject="alice")
    assistant.ingest([{"text": "refunds are processed within five business days",
                       "source": "refunds.md"}], subject="alice")
    answer = assistant.ask("how long do refunds take", subject="alice")
    assert "five business days" in answer["answer"]
    assert answer["grounding"] == "documents"
    assert answer["citations"]


class NearestNeighbours:
    """A store that answers every query with the same three documents.

    Not a strawman — it is what a vector index does. BM25 returns nothing when no
    term matches, so every test above ran with an empty `contexts` list on an
    off-topic question and never exercised the branch that decides between
    document and memory grounding. Qdrant has no such thing as no match: ask it
    about timezones and it hands back the nearest rows in the corpus, which are
    about refunds.

    The deployed stack failed exactly here — `grounding: "documents"`, three
    irrelevant citations, and an answer of "I don't know" with the caller's own
    timezone sitting in the `memories` field of the same response — while this
    suite was green. The fake is the difference between the two.
    """

    def __init__(self, texts: list[str]) -> None:
        self.chunks = [Chunk(text=t, source=f"doc-{i}") for i, t in enumerate(texts)]

    def add(self, docs: list) -> None:  # pragma: no cover - not what this proves
        pass

    def search(self, query: str, k: int = 3, tenant: str = "local") -> list[Chunk]:
        return self.chunks[:k]


def with_neighbours() -> Assistant:
    assistant = build_assistant(Settings())
    assistant.rag = NearestNeighbours([
        "approved refunds are processed within five business days",
        "staff are reimbursed for travel expenses within ten business days",
    ])
    return assistant


def test_irrelevant_neighbours_do_not_outrank_the_memory_that_answers():
    """The regression the vector store found and the fake now keeps.

    Retrieval returning something is not retrieval answering something. When
    nothing that came back bears on the question, the evidence class is whatever
    does — here, what the caller said about themselves."""
    assistant = with_neighbours()
    assistant.ask(ALICE_FACT, subject="alice")
    answer = assistant.ask("which timezone should we schedule in", subject="alice")
    assert "Lima" in answer["answer"]
    assert answer["grounding"] == "memory"
    # and the refund snippets that happened to be nearest are not offered as the
    # support for a statement about a timezone
    assert answer["citations"] == []


def test_relevant_neighbours_still_win_over_a_memory():
    """The other half: the filter must not turn every document answer into a
    memory one. Ask these same neighbours something they DO answer and the
    document is the ground, cited."""
    assistant = with_neighbours()
    assistant.ask(ALICE_FACT, subject="alice")
    answer = assistant.ask("how long do refunds take", subject="alice")
    assert "five business days" in answer["answer"]
    assert answer["grounding"] == "documents"
    assert answer["citations"]


def test_neighbours_that_answer_nothing_and_no_memory_still_abstain():
    assistant = with_neighbours()
    answer = assistant.ask("which timezone should we schedule in", subject="alice")
    assert answer["answer"] == ABSTAIN
    assert answer["grounding"] == "none"
