# Workshop · Your own MCP

Workshops 2–8 are one assistant. This phase is one folder of it.

Read [How to work with workshops](../workshops/README.md) first.

1. Open `src/workshops/assistant/phases/07-mcp/before`.
2. Edit `src/assistant/mcp_client.py` and `src/assistant/planner.py`. `mcp_server.py` is already finished.
3. Read the brief: [`WORKSHOP-MCP.md`](../workshops/assistant/phases/07-mcp/WORKSHOP-MCP.md).
4. Run `make setup`, then `make test`. The first failure is `test_discovered_tools_are_added_by_discovery_not_hardcoding`.
5. When `make test` is green, or you are stuck, diff those two files against the same paths under `../after`.
