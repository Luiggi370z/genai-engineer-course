# Workshop · Personal assistant

Workshops 2–8 are one assistant. This phase is one folder of it.

Read [How to work with workshops](../workshops/README.md) first.

1. Open `src/workshops/assistant/phases/04-agent/before`.
2. Edit `src/assistant/tools.py` and `src/assistant/agent.py`.
3. Read the brief: [`WORKSHOP-ASSISTANT.md`](../workshops/assistant/phases/04-agent/WORKSHOP-ASSISTANT.md).
4. Run `make setup`, then `make test`. The first failure is `test_readonly_tool_runs_and_finishes`.
5. When `make test` is green, or you are stuck, diff those two files against the same paths under `../after`.
