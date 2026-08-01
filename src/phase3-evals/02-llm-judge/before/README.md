# 3.2 LLM-as-judge

```bash
make setup && make test          # fails until the harness is implemented — no model needed
make test-integration            # the real RAGAS judge (needs Ollama running)
```

Two files, two tiers:

- `src/harness.py` — everything except the judge. Because the judge is **injected**,
  all of this is testable offline with a fake judge, and that is what `make test`
  does. Implement the TODOs here first.
- `src/ragas_judge.py` — the real RAGAS judge, pinned. Only the opt-in tier touches it.

The tests encode the two rules that matter: abstention rows must never reach the
judge, and results must be aggregated **per slice** as well as overall. One of them
(`test_slice_breakdown_exposes_what_the_average_hides`) fails if you only compute an
average — which is the failure mode this whole lesson exists to prevent.

Then point the harness at your Workshop-2 service instead of the stand-in pipeline
and read the slice table. It will tell you something you did not know about your own
RAG service.
