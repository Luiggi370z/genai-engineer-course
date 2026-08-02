# 3.1 The golden set — reference

**Test the dataset before you test the system.** Every score you will ever quote is
a property of these questions, so they get the same treatment as production code:
reviewed, versioned, sliced, and covered by tests.

```bash
make setup && make test        # the dataset's own gate — offline, no model
uv run python -m src.dataset   # the report you paste into a golden-set PR
```

## The five slices, and what each one buys you

| Slice | A failure here means | Why it must exist |
|---|---|---|
| `semantic` | paraphrase understanding broke | embeddings / chunking regressions |
| `exact` | the keyword arm is missing or broken | IDs and codes are where dense-only RAG dies |
| `multi_hop` | one chunk was never enough | catches retrieval depth, not just ranking |
| `unanswerable` | **the abstain path failed** | the most business-relevant behaviour you own |
| `adversarial` | a plausible-but-wrong neighbour won | stale versions, near-duplicate docs, false premises |

An overall average hides a collapsed slice. That is not a hypothetical: it is the
single most common way an eval suite gives false comfort.

## Two checks people skip

**Near-duplicates.** Two rows asking the same question in different words inflate
whichever slice they landed in and quietly reweight your average.

**Leakage.** A question copy-pasted out of a chunk scores well for the wrong
reason — the retriever is matching the question's own source text. You are
measuring string overlap and calling it retrieval quality.

Both are `rapidfuzz` one-liners, and both need `processor=default_process`: without
normalisation, one capital letter or comma drops a true duplicate under the
threshold (89.7 instead of 100 for a pair we tested while writing this lesson).

## Provenance is not bureaucracy

`source`, `labeled_by`, `labeled_on` on every row, and `supporting_doc_ids` on
every answerable row. The first three mean a reviewer can ask "why is this row
here?" and get an answer. The fourth is worth more than it looks: *did the
supporting doc appear in the top-k?* is a set-membership test, which means real
retrieval metrics with **no judge, no tokens, no network**.

## The rule that keeps it alive

Every production bug becomes a row. Freeze and version the file
(`golden.v3.jsonl`); editing a row so yesterday's failure passes is the most
common self-deception in this whole discipline.

## Fifty rows, in three sittings

Writing fifty golden rows in one go is the instruction most people abandon —
not because it is hard, but because nothing tells you anything until the end.
`src/milestones.py` breaks it into **10 / 25 / 50**, scores each sitting, and
prints what a score at that sample size is actually allowed to claim.

The milestones are motivation. The interval is the content. **8 of 10 is not
0.80** — it is 0.80 with a 95% interval of roughly 0.49–0.94, so a mediocre
system and a good one both produce 8/10 routinely. Ten rows is still far better
than zero and will find your obvious bugs on the first afternoon; it is simply
not yet a number you may quote, and `verdict()` says so in the report rather
than leaving you to remember it.

```bash
uv run python -c "from src.milestones import Interval, render; print(render(Interval(8, 10)))"
# overall: 0.80 (95% CI 0.49-0.94, n=10) - smoke test. Enough to find obvious
# breakage ... Not enough to compare two systems, and not enough to quote
```
