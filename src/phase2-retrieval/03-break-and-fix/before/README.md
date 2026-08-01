# 2.3 Break-and-fix

**Goal.** Diagnose a working-looking RAG pipeline that carries one planted bug —
the most common one in production RAG, and a silent one: nothing crashes, the
answers are just wrong. You practice the back-to-front debugging playbook, then
make the structural fix.
**Prerequisite.** 2.1 Eval harness (a cratering metric is how you'd notice this
in the wild) and 2.2 (you know the retrieval stack you're debugging).
**Effort.** ~25 min · gentle.

## Do this

```bash
make setup && make test     # 2 failing tests — the symptom, not the spec
$EDITOR src/rag.py          # read the playbook in the docstring, diagnose, then fix
make check                  # green: ruff + pyright + pytest, all offline
```

Work the playbook back-to-front: generation → retrieval → ingestion → ranking.

## What the first failure means

`test_retrieval_finds_the_payment_doc` fails: a payments question whose answer
sits verbatim in the corpus comes back citing a different document. No
exception, no warning — the answer reads fluently, it's just built on the wrong
context. That is the symptom you're diagnosing: retrieval returns nonsense while
every component *looks* healthy.

## Done when

- [ ] `make check` is green — both retrieval tests pass.
- [ ] The fix is structural (this failure mode can't quietly come back), not a
      patch that hard-codes the expected answers.
- [ ] You can name which eval metric from 2.1 would have caught this bug — then
      read `../after/README.md` for the full diagnosis.

## Stuck?

1. Walk the playbook from the answer backwards. Generation faithfully uses
   whatever context it's handed, and all three docs really are in the index —
   so which step is left?
2. When a document is indexed, retrievable in principle, and still loses to
   garbage with no error raised, suspect the *comparison* itself: check whether
   the ingestion path and the query path treat the text identically on their way
   into the vector store.

No integration lane: the embedders are injected and deterministic, so the bug —
and your fix — reproduce fully offline.
