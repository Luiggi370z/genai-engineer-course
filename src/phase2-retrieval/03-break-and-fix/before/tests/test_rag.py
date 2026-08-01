from src.rag import RAG

DOCS = [
    "invoice INV-88231 was paid on July third by wire transfer",
    "hybrid search fuses keyword and vector retrieval",
    "the weather is sunny today",
]


def test_retrieval_finds_the_payment_doc():
    """A payments question must retrieve the payments doc. FAILS until you fix the bug."""
    rag = RAG(DOCS)
    assert "invoice" in rag.answer("when was the invoice paid?").lower()


def test_retrieval_finds_the_search_doc():
    rag = RAG(DOCS)
    assert "hybrid search" in rag.answer("how does keyword and vector retrieval work?").lower()
