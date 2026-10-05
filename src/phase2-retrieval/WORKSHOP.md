# Workshop · Retrieval core

Workshops 2–8 are one assistant. This phase is one folder of it.

Read [How to work with workshops](../workshops/README.md) first.

1. Open `src/workshops/assistant/phases/02-rag/before`.
2. Edit `src/assistant/rag.py`. `provenance.py` is already finished.
3. Read the brief: [`WORKSHOP-RAG-SERVICE.md`](../workshops/assistant/phases/02-rag/WORKSHOP-RAG-SERVICE.md).
4. Run `make setup`, then `make test`. The first failure is `test_semantic_search`.
5. When `make test` is green, or you are stuck, diff only `rag.py` against `../after/src/assistant/rag.py`.
