# Verification stamp — `phase3-evals`

**Last verified:** 2026-08-01
**How:** every `after/` reference passed `make check` (ruff + pyright + pytest) on this date,
and every `before/` scaffold passed lint + type with its tests failing by design.

**What this stamp pins — and what it does not.** Ranges, not versions. Every lesson's
`pyproject.toml` declares upper-bounded *ranges* (`ragas>=0.4,<0.5`), so a fresh
`uv sync` resolves the newest release inside the range, which is usually — not
necessarily — what the date above was taken against. Where this file names an exact
version, that is a **record** of what the verified run resolved to, not a constraint
that reinstalls it. Exactly one lockfile is tracked in the whole repo,
`workshops/assistant/after/uv.lock`: the capstone's Python tree is the only one fixed by
hash rather than by range, because it is the only one that gets deployed. That still is
not a bit-reproducible image — its Dockerfile bases are floating tags and the stack
pulls its models by tag, both deliberately, so a rebuild picks up Debian's security
patches instead of pinning a known-vulnerable layer. Everything else is version-bounded.
Interpreter: **3.11 through 3.14** (`>=3.11,<3.15`), with both ends run in CI on every
push; `phase4-agents/04-framework-bakeoff` pins 3.12 and says so itself. The long version is in [`../README.md`](../README.md).
Lesson 3.2's judged tier (`make test-integration`) was additionally run against a real
local judge on Ollama.

## What was verified against what

| Lesson | Library surface exercised | Version |
|---|---|---|
| 3.1 `01-golden-set` | `rapidfuzz` `fuzz.token_set_ratio` / `partial_ratio` with `utils.default_process` | rapidfuzz 3.14 |
| 3.2 `02-llm-judge` | `ragas.metrics.collections.{Faithfulness,ContextRecall}` + `ragas.llms.llm_factory` | **ragas 0.4.3** |
| 3.3 `03-judge-calibration` | `sklearn.metrics.cohen_kappa_score` | scikit-learn 1.9 |
| 3.4 `04-ci-regression-gate` | stdlib only — the gate is pure logic over two JSON files | — |

## RAGAS moved, and this is where it moved to

As of 0.4.x the metric classes live in **`ragas.metrics.collections`** and take an
explicit judge built with `ragas.llms.llm_factory`. The older
`from ragas.metrics import Faithfulness` path still imports but raises a
`DeprecationWarning` pointing at the new one, and `evaluate()` / `EvaluationDataset`
belong to that older surface. Metric instances expose `ascore()` and a synchronous
`score()`, both returning a `MetricResult` — read `.value`.

## The pin that is not optional

Installing `ragas>=0.4,<0.5` with nothing else constrained resolved
`langchain-community` 0.4, and the judged tier died on import:

```
ModuleNotFoundError: No module named 'langchain_community.chat_models.vertexai'
```

`ragas.llms.base` still imports a module that langchain-community 0.4 removed. Lesson
3.2 therefore pins `langchain-community>=0.3.27,<0.4` alongside `ragas` as a
known-good pair. This is exactly why the judged tier is an optional dependency group:
a transitive dependency of your *judge* must never be able to break the gate that
runs on every push.

If a lesson here fails to install, read the date above, then the lesson's
`pyproject.toml` — the pin says what it was built against. Upgrade one dependency at
a time and re-run `make check`.
