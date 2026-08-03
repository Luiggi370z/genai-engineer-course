# 2.1 Eval harness — reference

**Two tiers, because that's how real teams run evals.**

| Tier | Command | What it is | When |
|---|---|---|---|
| 1 · non-LLM | `make test` | `rapidfuzz` string metrics — deterministic, free, offline | every PR |
| 2 · real RAGAS | `make test-integration` | `ragas` + pinned LLM judge (free on Ollama) | nightly / pre-merge |

Tier 2's *arithmetic* runs on every PR too, in `tests/test_gate.py`: `as_score` and
`aggregate` are pure functions, so the mean, the score-range guard, the NaN case and
both sides of each threshold are tested offline with no judge and no `ragas`
installed. That works because `src/ragas_eval.py` imports ragas inside the functions
that need it, and it is the difference between a gate you have tested and a gate you
have run. A live judge can tell you its verdict; only a test can tell you that a NaN
verdict fails the build instead of passing it.

Tier-1 metrics are named `*_nonllm` **on purpose**: they measure lexical
similarity, not semantic faithfulness. RAGAS ships the same family
(`NonLLMContextRecall`). Never report a lexical proxy as "faithfulness."

Two things that bite people, both handled in `src/ragas_eval.py`:
**pin the judge** (model + `temperature=0` — the judge is part of the ruler), and
**pin RAGAS's dep tree** (it wraps LangChain and moves fast).

**The API, verified against ragas 0.4.3 (2026-07-31).** Metrics come from
`ragas.metrics.collections` and take a judge built by `ragas.llms.llm_factory`
over an `openai.AsyncOpenAI` client; they score one sample at a time through
`score(...)`, so the averaging is yours. The pre-0.4 surface — `from
ragas.metrics import Faithfulness` with `evaluate()` and `EvaluationDataset` —
still imports and raises a DeprecationWarning, which is the worst failure mode
available: old code keeps working just long enough to get copied. This lesson and
lesson 3.2 sit on the same surface and the same pin, and `check-claims` fails the
build if the two drift, because a course that teaches two APIs for one library
gives the reader no way to tell which half is current.

The golden set is sliced (`semantic` / `exact` / `unanswerable`) so a failure
tells you *where* you're weak — exact-match is usually the culprit, which is
exactly what lesson 2.2 fixes.

## Six rows here, thirty in yours

`evals/golden.jsonl` holds **six** rows: three `semantic`, two `exact`, one
`unanswerable`. That is a fixture. It is enough to prove the harness loads, scores,
slices and gates, and deliberately too small to conclude anything about a retrieval
system — the whole unanswerable slice is one question, so that slice's mean is either
0.0 or 1.0 and can never be anything else.

The workbook exercise asks for **thirty** over your own corpus — 15 semantic, 10
exact-match, 5 unanswerable. Ten per slice is roughly where a slice mean stops
being anecdote. `test_golden_set_loads_with_slices` therefore asserts a **floor**
of six and the presence of all three slices, never `== 6`: growing your eval set is
the assignment, and a test that fails when you do it teaches the opposite lesson.

Write the questions the way users type them, not the way your documents are worded.
A golden set paraphrased out of the corpus measures whether the retriever can find
text it was handed; the exact-match slice especially needs the real error codes,
invoice formats and product names people actually paste in.

**What is and is not in scope here.** This lesson builds both tiers and gates on
tier 1. Tier 2 runs the same golden set past a real judge so you can see the two
disagree. Deciding *which one is right* — sampling rows, labelling them yourself,
measuring how often the judge agrees with you, and only then trusting a judged
number as a gate — is calibration, and it is Phase 3's subject, not this one.

## Known dependency friction (verified 2026-07-30)

RAGAS wraps LangChain, and that dependency tree moves fast. While building this
lesson, a fresh `ragas` install resolved to a version whose import chain broke
against the installed `langchain-community`:

```
ModuleNotFoundError: No module named 'langchain_community.chat_models.vertexai'
```

That is exactly why tier 2 is an **optional dependency group** rather than part of
`make test`: a heavy transitive tree should never be able to break your fast gate.
If you hit it, pin `ragas` and `langchain-community` together as a known-good pair
and upgrade them deliberately.
