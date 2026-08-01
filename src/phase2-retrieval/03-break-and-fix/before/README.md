# 2.3 Break-and-fix

A working-looking RAG pipeline with one planted bug — the most common one in
production RAG, and a *silent* one.

```bash
make setup && make test     # one test fails; hunt it with the playbook
```

Work back-to-front: generation → retrieval → ingestion → ranking. When you've
fixed `src/rag.py` and it's green, name which eval metric would have caught it,
then read `../after/README.md`.
