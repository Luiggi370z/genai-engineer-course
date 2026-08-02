# ADR-0003 — Approvals as consumable grants with idempotency keys

**Status:** accepted

## Context

An irreversible tool (send a message, delete a file) must not fire without a
human decision — and the decision machinery itself must not create new ways to
fire twice. Two real-world bugs shape this: a client retrying `/approve` after a
timeout, and an approval that silently stays valid forever.

## Decision

`/approve` increments a per-tool grant counter; the agent loop treats a tool as
approved only while its count is positive; every run of a gated tool consumes one
grant (`_consume_grants`). A retried `/approve` carrying the same
`Idempotency-Key` is recognized by the SQLite dedupe table and does not mint a
second grant. Every grant, replay and gated run lands in the persistent audit log
with the caller's identity.

## Alternatives considered

Boolean approvals (approve once, fire forever — fails the "single-use" property
the reliability tests pin); approving by conversational text ("yes go ahead" —
indistinguishable from an injected approval, see ADR-0002); a full workflow
engine with pending-task queues (right for multi-approver processes, out of
proportion here and it would bury the mechanism being taught).

## Consequences

"Approved once" provably means "fires once" (`test_reliability.py`,
`test_security.py`, e2e check 6). Cost: a legitimate second execution needs a
second explicit approval — accepted, that is the semantics a human reviewer
expects of an irreversible action.
