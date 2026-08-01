# 6.1 Red-team

**Goal.** Harden a naive agent with layered guardrails (decode+scan, spotlight, an L3 output gate) and prove it with a shipped red-team suite of ~30 rows across direct, indirect, encoded, mutated, and PII attack families plus benign controls. The bar is containment — no landed injection fires a gated tool — not zero landings.
**Prerequisite.** 4.3 Human-in-the-loop (tool gating and approval).
**Effort.** ~45 min · moderate

## Do this

```bash
make setup && make test     # 5 failing tests — read them, they are the spec
$EDITOR src/guardrails.py   # decode_and_normalize, spotlight, layer1, layer3_output_ok
$EDITOR src/agent.py        # guarded_run: wire the layers around the naive agent
make check                  # green: ruff + pyright + pytest, all offline
```

## What the first failure means

The dataset breadth test already passes — `evals/redteam.jsonl` ships complete with 31 rows. The first failure is `test_direct_injections_are_blocked_outright`: `layer1` raises `NotImplementedError`, so not even "ignore all previous instructions" gets blocked. Build the input gate first (length cap, injection patterns, PII redaction), then work outward to encoded payloads and the containment property in `guarded_run`.

## Done when

- [ ] `make check` is green (lint, types, fast tests).
- [ ] `test_landed_injections_cannot_fire_a_gated_tool` passes: every case with retrieved content — including the mutated payloads that slip past L1 — neither fires an irreversible tool without approval nor leaks PII.
- [ ] `test_benign_requests_are_not_false_positives` passes: the benign controls still get through, so the filter isn't just blocking everything.

## Stuck?

1. The mutated rows are *supposed* to get past L1's regexes. That's the point of layering: containment comes from `guarded_run` keeping gated tools behind approval and gating the output, not from a perfect input filter.
2. In `decode_and_normalize`, find base64-looking spans, decode them, and append the decoded text before scanning — then `layer1` catches encoded payloads with the same `INJECTION` patterns. In `guarded_run`, treat retrieved docs as untrusted: run them through `layer1`/`spotlight` and never let their instructions reach a tool decision.

No integration lane: the guardrails are pure Python (regex + policy) — no model or service needed to prove containment.
