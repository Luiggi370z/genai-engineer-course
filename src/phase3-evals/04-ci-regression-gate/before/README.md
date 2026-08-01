# 3.4 The CI regression gate

An eval you run by hand when you remember to is a vibe with extra steps. This lesson
is the boring mechanical part that makes the previous three real.

```bash
make setup && make test    # fails until the gate is implemented
make gate                  # exactly what CI runs
```

Implement `src/gate.py` so that `make gate` fails on:

- an **absolute bar** breach (`faithfulness < 0.85`, `context_recall < 0.80`);
- a **regression** against `evals/baseline.json` beyond `TOLERANCE`;
- a **per-slice** regression — including a slice that collapsed or vanished;
- **instrument drift** — a different judge, temperature or library version means the
  numbers aren't comparable.

`evals/results.json` is a real-shaped run that **passes on purpose**: it dips 0.015 on
faithfulness, which is inside the noise floor lesson 3.3 measured. A gate that fires
on noise is a gate people learn to route around.

Then wire it up: copy `ci/evals.yml` to `.github/workflows/` in your own repo. Fast
tier on every pull request, judged tier nightly.

One rule to take with you: **re-baselining is a human decision.** Review the diff and
commit the new baseline in its own PR with a note about why the number moved. A gate
that updates its own baseline is a gate that never fails.
