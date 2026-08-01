# 6.1 Red-team — reference

Layered guardrails (decode+scan, spotlight, L3 gate) + least-privilege + HITL, proven by a red-team suite of ~30 rows across direct, indirect, encoded, **mutated**, and PII attack families plus **benign controls** (so the filter isn't just blocking everything). Bar = containment: no landed injection fires a gated tool. The mutated rows are expected to slip past L1 — they're there to prove the HITL backstop holds anyway.
