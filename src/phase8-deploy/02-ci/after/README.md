# 8.2 CI — reference

Four gates, four independent failures: `make eval` runs the quality gate (faithfulness/recall bars), `make redteam` the safety gate (zero bypasses), and `make latency` / `make cost` the P99 and spend budgets — all through the CLI in `src/gate.py`, all over a VERSION-STAMPED report (model/prompt/corpus/dataset). An unstamped report blocks every gate: numbers without provenance are not evidence. The four are separate jobs rather than one averaged score because a safety bypass, a quality regression, a latency blowout and a cost blowout are different incidents with different owners. `make prove-gates` runs the seeded regressions in `evals/seeded/` and demands each one blocks — a gate that cannot fail is decoration.

The `evals/report.json` here is a **fixture**: it exists so the policy is testable offline, in one lesson, without booting a stack. Do not mistake it for the thing being measured. A gate that reads a committed report only ever checks that somebody remembered to edit a file, and the number it blesses was true whenever it was last pasted in.

The same idiom, one level up: `make defect-lab` in `workshops/assistant/after` applies
seeded regressions to *code* rather than to a report. Three vulnerabilities the capstone
actually shipped are kept as running variants, and each regression test must pass against
the current code and then fail with its defect seeded back in. Green first, then red —
because "it went red" is only evidence if the test was capable of being green, and an
unwritten test otherwise reads exactly like a caught defect. See `WORKSHOP-DEFECT-LAB.md`.

The real gate lives in the repo-root workflow, `.github/workflows/ci.yml` — the only place GitHub actually looks, which is why this lesson no longer ships a `.github/` of its own that would never run. Its `evidence` job builds the capstone image from the current commit, runs `python -m assistant.report` **inside that image**, and puts this same CLI in front of the report that run produced. Locally the same thing is one command: `make gate` in `workshops/assistant/after`. The version stamps are derived there rather than typed — `prompt` is a hash of the prompt builder's own source, so editing the prompt and leaving the label alone is not possible.
