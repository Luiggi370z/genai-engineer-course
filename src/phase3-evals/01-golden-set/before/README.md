# 3.1 The golden set

The dataset is the product. Before you compute a single score, make the questions
themselves defensible — and prove it with tests.

```bash
make setup && make test        # fails until you implement the checks
uv run python -m src.dataset   # the report you'll paste into a golden-set PR
```

## Your job, in two halves

**1 · Implement the checks** in `src/dataset.py` (`rapidfuzz`, offline, no model).

**2 · Fix `evals/golden.jsonl`.** The shipped file has real problems planted in it:
a missing slice, an abstain slice too thin to mean anything, a duplicate question
someone added in a hurry, a question pasted straight out of a chunk, and a row with
no provenance. Your checks are how you find them; `validate()` returning `[]` is how
you know you're done.

## Then do it on your own corpus

Grow the set to ~50 rows over the corpus behind your Workshop-2 RAG service:
roughly 20 `semantic`, 12 `exact`, 8 `multi_hop`, 7 `unanswerable`, 3 `adversarial`.
Every row carries its `source` — where the question came from — and every
answerable row names its `supporting_doc_ids`. That last field is what gives you
retrieval metrics with no judge at all.

The unanswerable rows are not filler. A set of only answerable questions rewards a
system that always answers, and your abstain path is the behaviour the business
cares about most.
