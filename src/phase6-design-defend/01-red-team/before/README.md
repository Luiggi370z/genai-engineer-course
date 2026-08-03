# 6.1 Red-team

**Goal.** Harden a naive agent with layered guardrails (decode+squash+scan, spotlight, an L3 output gate) and prove it with a shipped red-team suite of 58 rows: 47 attacks across direct, indirect, encoded, mutated, multilingual, exfiltration, approval-bypass, tool-output and PII families, and 11 benign controls. The bar is containment — no landed injection fires a gated tool — but a detector you cannot see fire is a detector you cannot trust, so you will also count what got dropped.
**Prerequisite.** 4.3 Human-in-the-loop (tool gating and approval).
**Effort.** ~60 min to green on the fast tests · no integration tier · ~95 min realistic first pass.

## Do this

```bash
make setup && make test     # 9 failing tests — read them, they are the spec
$EDITOR src/guardrails.py   # decode_and_normalize, squash, looks_like_injection, layer1, ...
$EDITOR src/agent.py        # guarded_run: screen BOTH untrusted channels, count the drops
make check                  # green: ruff + pyright + pytest, all offline
```

## What the first failure means

The dataset breadth test already passes — `evals/redteam.jsonl` ships complete at 58 rows. The first real failure is `test_direct_injections_are_blocked_outright`: `layer1` raises `NotImplementedError`, so not even "ignore all previous instructions" gets blocked. Build the input gate first (length cap, injection patterns, PII redaction), then the two scan surfaces, then the containment property in `guarded_run`.

## Two surfaces, because attackers work two ways

**Expansion** asks *what else does this text say* — base64, `%20`, `&#105;`. Each decoding is appended, never substituted, so a decode that goes wrong costs a false positive rather than losing the original.

**Squashing** asks *what does this say if you stop respecting the separators*. `1gn0re`, `i g n o r e`, `Ign<zero-width-space>ore`, `ｉｇｎｏｒｅ` and `I-G-N-O-R-E` are one word to a reader and five different strings to a regex. Squash lowercases, NFKC-folds, drops the invisible `Cf` characters, folds leet digits, and deletes everything that is not a letter or digit — then you match patterns written the same way.

Both surfaces need controls, and this suite ships them: a base64 *filename*, a percent-encoded URL, an ampersand in a company name, a hyphenated word, and the word "ignore" used honestly. A filter that blocks all five is not a filter, it is an outage.

## Done when

- [ ] `make check` is green (lint, types, fast tests).
- [ ] `test_landed_injections_cannot_fire_a_gated_tool` passes: every case carrying untrusted content neither fires an irreversible tool without approval nor leaks PII.
- [ ] `test_every_poisoned_channel_is_detected_and_dropped_not_merely_survived` passes: for every case, the number of dropped items *equals* the number of poisoned ones — no more, no fewer.
- [ ] `test_benign_requests_are_not_false_positives` passes: all 11 controls still get through.

## Stuck?

1. Squash the *expansion*, not the original — a base64 payload needs both treatments, and doing them in the wrong order means a leetspeak sentence hidden in base64 walks straight through.
2. In `guarded_run`, both channels get the same treatment: `retrieved` and `tool_outputs` are one list of untrusted items. Screen each, DROP the ones that fail (do not sanitise — there is no safe half of an instruction), spotlight what survives, and record `screened_untrusted` / `dropped_untrusted` so the test can tell "contained" from "detected".
3. When the user's own message is refused at the door, the untrusted channel is never reached — so those cases have nothing to drop, and the test skips them. If your counts are off by a few, that is usually why.

## Why counting matters more than it looks

Containment (HITL, least privilege) holds the line whether or not the screen ever fires. So a suite that only asserts "nothing bad happened" passes just as happily with the detector deleted. The day someone breaks `squash` you would find out from an incident, not from CI. Counting the drops is what turns a safety property into a regression test.

No integration lane: the guardrails are pure Python (regex + policy) — no model or service needed to prove containment.
