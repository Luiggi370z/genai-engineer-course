# 8.4 Cost & latency — your turn

Climb the ladder in order and prove each rung with a number:

1. **Exact cache** — a key over everything that changes the answer (not just the
   question), plus a TTL you chose on purpose.
2. **Semantic cache** — reuse a *similar* question above a threshold, and use
   `sweep` to pick that threshold with evidence rather than a shrug.
3. **Tier router** — cheap work to a cheap model, with a cost ceiling that steps
   down one rung and *records* the downgrade.
4. **Budget gate** — fail on P99, on cost per request, and on the eval score.
   Report cost and quality together or don't report the saving.

```bash
make setup && make check
make test-integration    # the semantic cache against a real embedding model
```

Rungs 1 and 2 cannot change an answer. Rungs 3 and 4 can. That asymmetry is the
reason for the order — and the reason the gate takes a quality score it did not
compute itself.
