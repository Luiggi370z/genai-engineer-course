# Architecture Decision Records

Five decisions that shape the capstone, each with the alternatives it beat and
the cost it accepted. Read them with [`../ARCHITECTURE.md`](../ARCHITECTURE.md)
open — the diagrams show *what*, these say *why*.

| ADR | Decision |
|---|---|
| [0001](0001-ports-and-adapters-tiered-by-env.md) | Ports and adapters, tiered by environment variables |
| [0002](0002-guardrails-at-every-trust-boundary.md) | Guardrails at every trust boundary, spotlighting over trust |
| [0003](0003-approvals-as-consumable-grants.md) | Approvals as consumable grants with idempotency keys |
| [0004](0004-otel-spans-as-the-observability-currency.md) | OpenTelemetry spans as the only observability currency |
| [0005](0005-sqlite-for-state.md) | SQLite for memory, audit and idempotency — one file, not three services |

The format is deliberately short (context → decision → alternatives →
consequences). An ADR nobody reads is a decision nobody can challenge; these fit
on one screen each so they actually get read.
