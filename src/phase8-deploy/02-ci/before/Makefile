include ../../../_lesson.mk

# The two gate targets the workflow calls. Real, local, and fast: they run the merge
# policy over a committed report so `make eval` / `make redteam` mean something on a
# laptop, not just in CI. In your own repo these point at the capstone's eval suite
# and red-team fixture (workshops/assistant: `make gate`, phase6 red-team).
.PHONY: eval redteam
eval:             ## quality gate: fail if faithfulness/recall regressed
	uv run python src/gate.py --quality evals/report.json
redteam:          ## safety gate: fail if any gated tool fired unapproved
	uv run python src/gate.py --safety evals/report.json
