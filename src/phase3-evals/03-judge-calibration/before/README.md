# 3.3 Judge calibration

How do you know the judge is right? You labeled some rows yourself and measured the
overlap. That is the whole lesson, and almost nobody teaches it.

```bash
make setup && make test              # fails until you implement it — no model needed
uv run python -m src.calibration     # the report you keep next to your scores
```

`evals/labeled.jsonl` has 40 rows you labeled `pass`/`fail`, each with the judge's raw
score. Implement `src/calibration.py` until the tests pass, then read what the report
tells you:

- **Report kappa, not agreement.** One test builds a judge that says "pass" to
  everything against a 90%-pass set: agreement 0.90, kappa 0.00. Same rubber stamp.
- **Sweep the threshold.** 0.5 is a round number, not a decision. On this fixture the
  swept threshold moves agreement by 7 points and kappa by 21 — across the line where
  gating merges becomes defensible.
- **Derive the CI tolerance** from the disagreement rate. Lesson 3.4's gate uses it.
- **Read the disagreements.** Each one is a bad rubric, a bad label, or a question too
  ambiguous to be in the golden set. Fix whichever it is.

Then do it for real: label 30–50 rows from your own judged run (lesson 3.2) and write
down the kappa you are willing to quote alongside your scores.
