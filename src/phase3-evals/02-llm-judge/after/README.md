# 3.2 LLM-as-judge — reference

```bash
make setup && make test          # the whole harness, offline, no model
make test-integration            # the real RAGAS judge (needs Ollama running)
```

## The design decision that makes evals testable

**The judge is injected.** `src/harness.py` knows how to run a golden set, when a
row needs a judge at all, how to aggregate per slice, and what to record next to the
numbers — none of which requires a model. So all of it is covered by the fast tier,
and the only thing behind `make test-integration` is the judge itself
(`src/ragas_judge.py`).

That is why `make test` here needs nothing but `pytest`.

| Tier | Command | What it proves | When |
|---|---|---|---|
| fast | `make test` | The grading logic is right | every push |
| judged | `make test-integration` | The judged path still works against today's library and model | nightly / pre-merge |

## Two rules baked into the harness

**Abstention rows are scored without the judge.** "Did the system refuse?" is a
string check. Sending it to an LLM adds cost, latency and noise to the one slice you
least want noise in.

**Aggregate per slice, always.** `test_slice_breakdown_exposes_what_the_average_hides`
is the whole lesson in one test: the unanswerable slice sits at 0.00 while the
overall mean stays above 0.75. Averages are where regressions go to hide.

## The current RAGAS API (verified against 0.4.3 on 2026-07-31)

```python
from openai import AsyncOpenAI
from ragas.llms import llm_factory
from ragas.metrics.collections import ContextRecall, Faithfulness

judge = llm_factory("qwen3-coder:30b",
                    client=AsyncOpenAI(base_url="http://localhost:11434/v1",
                                       api_key="ollama"),
                    temperature=0)
Faithfulness(llm=judge).score(user_input=q, response=answer,
                              retrieved_contexts=contexts).value
```

- Metric classes live in **`ragas.metrics.collections`** and take an explicit judge.
  The older `from ragas.metrics import Faithfulness` path still imports but raises a
  `DeprecationWarning` pointing here; `evaluate()` and `EvaluationDataset` belong to
  that older surface.
- Instances expose `ascore(...)` and a synchronous `score(...)`. Both return a
  `MetricResult` — read `.value`.
- Any Ollama model speaks the OpenAI API, so **one code path serves a local judge
  and a hosted one**. That is what makes calibration (lesson 3.3) actionable: you
  can compare a free judge against a paid one on the same rows.

## Dependency friction, first-hand (2026-07-31)

Installing `ragas>=0.4,<0.5` with no other constraint resolved
`langchain-community` 0.4, and the judged tier died on import:

```
ModuleNotFoundError: No module named 'langchain_community.chat_models.vertexai'
```

`ragas.llms.base` still imports that module, which 0.4 removed. The fix is in
`pyproject.toml`: pin `langchain-community>=0.3.27,<0.4` as a known-good pair with
`ragas` and upgrade them together, deliberately.

This is also the argument for the two tiers: a transitive dependency of your *judge*
should never be able to break the gate that runs on every push.

## Pinning the ruler

1. **The judge model** — model plus `temperature=0`, recorded in every results file
   by `describe()`. A score without its instrument is not a measurement.
2. **The generator must not be the judge.** Models favour their own family's
   writing.
3. **The library** — see above.
