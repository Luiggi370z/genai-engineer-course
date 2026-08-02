# 6.1 Red-team — reference

Layered guardrails (decode + squash + scan, spotlight, L3 gate) + least-privilege + HITL, proven by a red-team suite of **58 rows** (version 3) across direct, indirect, encoded, mutated, multilingual, exfiltration, approval-bypass, tool-output and PII families, plus **11 benign controls** — one per detector, so the filter cannot pass by blocking everything. Bar = containment: no landed injection fires a gated tool.

**Two scan surfaces.** `decode_and_normalize` expands (base64, percent-encoding, HTML entities), appending each decoding rather than substituting it. `squash` removes the separators an attacker hides behind: NFKC folding, Unicode `Cf` (zero-width space, soft hyphen) stripping, leet folding, then everything non-alphanumeric deleted. `SQUASHED_INJECTION` patterns are written without separators to match it. Together they close the obfuscation gap that earlier versions of this lesson left open on purpose — `1gn0re`, `i g n o r e`, `Ign<ZWSP>ore`, `ｉｇｎｏｒｅ` and `I-G-N-O-R-E` are now all one string.

**Both untrusted channels are screened, not just spotlighted.** `guarded_run` runs every retrieved document *and* every tool output through L1 and **drops** the ones that fail. Spotlighting stops a clean-looking document from being read as an instruction; dropping stops the dirty ones from getting that far.

**The counting assertion.** `test_every_poisoned_channel_is_detected_and_dropped_not_merely_survived` requires `dropped_untrusted` to *equal* the number of poisoned items — not "≥ 1", and not just "nothing bad happened". Containment holds the line whether or not the detector fires, so a suite that only checks the outcome passes just as happily with the screen deleted; the count is what makes the detector itself a regression test.
