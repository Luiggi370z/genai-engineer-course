# Workshop · Hardened assistant

Workshops 2–8 are one assistant. This phase is one folder of it.

Read [How to work with workshops](../workshops/README.md) first.

1. Open `src/workshops/assistant/phases/06-hardened/before`.
2. Edit `src/assistant/guardrails.py`, `src/assistant/screening.py`, and `src/assistant/guard.py`.
3. Read the brief: [`WORKSHOP-HARDENED.md`](../workshops/assistant/phases/06-hardened/WORKSHOP-HARDENED.md).
4. Run `make setup`, then `make test`. The first failure is `test_screen_blocks_injection`.
5. When `make test` is green, or you are stuck, diff those files against the same paths under `../after`.
