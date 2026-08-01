# Workshop · Personal assistant  (ends Phase 4)

Give the assistant an agent loop and real tools: read email, read news, send a
Telegram message, schedule an event. Everything is a tool; sends/schedules are
gated behind human approval.

## Deliverables
- [ ] Read + summarize email (read-only tool, no gate)
- [ ] Fetch + summarize a news page
- [ ] `send_telegram` and `schedule_event` work AND pause for approval first
- [ ] Every connector is a proper tool: docstring, validation, error-as-data
- [ ] Hard step cap in the loop; credentials from env vars

Implement `tools.py` + `agent.py`. Tests: `tests/test_agent.py`.
