# Workshop · Your own MCP, used by the assistant  (ends Phase 7)

Build an MCP server for a service you care about (see `phase7-mcp/02-rest-to-mcp`),
then let the assistant gain its tools by **discovery** — not hard-coding.

## Deliverables
- [ ] `extend_assistant()` merges discovered MCP tools into the toolbox
- [ ] Discovered tools carry their `requires_approval` flag (gating still applies)
- [ ] The assistant can call a discovered tool through the agent loop
- [ ] Adding a tool to the server makes it usable with NO assistant code change
- [ ] (production) real MCP server with correct auth (Phase 7)

Implement `mcp_client.py`. Tests: `tests/test_mcp.py`.
