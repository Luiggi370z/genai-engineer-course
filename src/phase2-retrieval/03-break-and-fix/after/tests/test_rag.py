from src.rag import RAG, embedder_a, embedder_b

DOCS = [
    "invoice INV-88231 was paid on July third by wire transfer",
    "hybrid search fuses keyword and vector retrieval",
    "the weather is sunny today",
]


def test_retrieval_finds_the_payment_doc():
    rag = RAG(DOCS)
    assert "invoice" in rag.answer("when was the invoice paid?").lower()


def test_retrieval_finds_the_search_doc():
    rag = RAG(DOCS)
    assert "hybrid search" in rag.answer("how does keyword and vector retrieval work?").lower()


def test_the_bug_is_reproducible_on_demand():
    """Regression guard: mixing embedders MUST break retrieval.

    This is the test that would have caught the original bug. Note it doesn't
    crash — it silently returns the wrong document, which is why the bug is so
    common and so hard to spot without an eval.
    """
    rag = RAG(DOCS, embed=embedder_a)          # index with A
    good = rag.retrieve("when was the invoice paid?", k=1)
    rag.embed = embedder_b                      # query with B — the drift
    bad = rag.retrieve("when was the invoice paid?", k=1)
    assert good != bad
    assert "invoice" in good[0].lower()
    assert "invoice" not in bad[0].lower()
