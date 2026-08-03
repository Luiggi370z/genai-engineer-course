# 2.1 Eval harness — reference

**Two tiers, because that's how real teams run evals.**

| Tier | Command | What it is | When |
|---|---|---|---|
| 1 · non-LLM | `make test` | `rapidfuzz` string metrics — deterministic, free, offline | every PR |
| 2 · real RAGAS | `make test-integration` | `ragas` + pinned LLM judge (free on Ollama) | nightly / pre-merge |

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
