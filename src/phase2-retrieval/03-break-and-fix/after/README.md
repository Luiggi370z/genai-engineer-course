# 2.3 Break-and-fix — diagnosis

**Symptom:** retrieval returned nonsense for questions whose answers are verbatim
in the corpus. Nothing crashed. `context_recall` cratered.

**The bug:** a **mismatched embedding model** — documents were indexed with
`embedder_a`, queries embedded with `embedder_b`. Both produce 3-dimensional
vectors, so Qdrant accepted them happily; but the two models put different
meanings on different axes, so cosine similarity between them is noise.

**Why it's the most common RAG bug in the wild:** it's *silent*. Same dimension =
no exception, no warning, no log line. You only notice through evaluation — which
is precisely why lesson 2.1 comes first.

**Walking the playbook:**
1. Answer ignoring context? No — generation was fine.
2. Right doc retrieved? No.
3. Doc in the index? Yes, all three were indexed.
4. → so the *comparison* is broken, not the storage. Check that the query path
   and the index path use the **same** embedder. They didn't.

**Which metric caught it:** `context_recall` — retrieval couldn't fetch what the
reference needed. Faithfulness alone would have looked "fine" (the model was
faithfully summarizing the wrong document).

**The structural fix:** one injected embedder used by both paths, so they can't
drift. In production, also record the model name (and version) in the collection
metadata and refuse to query if it doesn't match — re-embed on model change.

`test_the_bug_is_reproducible_on_demand` is the regression guard that would have
caught it originally.
