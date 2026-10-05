# Workshop · Eval suite

Workshops 2–8 are one assistant. This phase is one folder of it.

Read [How to work with workshops](../workshops/README.md) first.

1. Open `src/workshops/assistant/phases/03-evals/before`.
2. Edit `src/assistant/evals.py`.
3. Read the brief: [`WORKSHOP-EVAL-SUITE.md`](../workshops/assistant/phases/03-evals/WORKSHOP-EVAL-SUITE.md).
4. Run `make setup`, then `make test`. The first failure is `test_the_suite_scores_every_slice`.
5. When `make test` is green, or you are stuck, diff only `evals.py` against `../after/src/assistant/evals.py`.
