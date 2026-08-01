# Workshops · the evolving assistant

Workshops 2 through 8 build **one** personal assistant that grows across the course.
The two bookends live elsewhere: Workshop 1, the model bench, in `../model-bench/`,
and Workshop 9, the interview loop, in `../interview-loop/` (markdown only — the
artifact is a habit, not a repo).
`before/` is your scaffold (TODOs); `after/` is the working reference.

| Workshop | Ends phase | Adds | Files | Brief |
|----------|-----------|------|-------|-------|
| RAG service | 2 | hybrid-retrieval core | `rag.py` | `WORKSHOP-RAG-SERVICE.md` |
| Eval suite + CI gate | 3 | golden set, injectable judge, calibration, gate | `evals.py` | `WORKSHOP-EVAL-SUITE.md` |
| Personal assistant | 4 | agent loop, tools, HITL | `tools.py`, `agent.py` | `WORKSHOP-ASSISTANT.md` |
| Memory + research crew | 5 | memory with TTL + provenance, budgeted context, tiered delegation | `memory.py`, `crew.py` | `WORKSHOP-MEMORY-CREW.md` |
| Hardened assistant | 6 | guardrails, spotlighting, output gate | `guardrails.py` | `WORKSHOP-HARDENED.md` |
| Your own MCP | 7 | consume an MCP server by discovery | `mcp_client.py` | `WORKSHOP-MCP.md` |
| Deployed stack | 8 | OTel spans around the loop and every tool, answer cache with refusal rules | `observe.py`, `cache.py` | `WORKSHOP-DEPLOYED-STACK.md` |

Do them in order — each builds on the last, and from the eval layer onwards every
later layer is measured by the one before it.

```bash
cd after && make check     # the reference passes; your job is to make before/ pass
```
