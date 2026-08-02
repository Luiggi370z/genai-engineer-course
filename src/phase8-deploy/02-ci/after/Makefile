include ../../../_lesson.mk

# The gate targets the workflow calls. Real, local, and fast: they run the merge
# policy over a committed report so `make eval` / `make redteam` / `make latency`
# / `make cost` mean something on a laptop, not just in CI. In your own repo these
# point at the capstone's eval suite and red-team fixture (workshops/assistant:
# `make gate`, phase6 red-team).
.PHONY: eval redteam latency cost prove-gates
eval:             ## quality gate: fail if faithfulness/recall regressed
	uv run python src/gate.py --quality evals/report.json
redteam:          ## safety gate: fail if any gated tool fired unapproved
	uv run python src/gate.py --safety evals/report.json
latency:          ## latency gate: fail if P99 exceeds the budget
	uv run python src/gate.py --latency evals/report.json
cost:             ## cost gate: fail if the golden-set run exceeds the budget
	uv run python src/gate.py --cost evals/report.json

prove-gates:      ## every seeded regression must BLOCK — a gate that can't fail isn't a gate
	@for f in evals/seeded/*.json; do \
	  if uv run python src/gate.py "$$f" >/dev/null 2>&1; then \
	    echo "GATE FAILED TO BLOCK: $$f"; exit 1; \
	  else \
	    echo "blocked as expected: $$f"; \
	  fi; \
	done
	@echo "prove-gates: all seeded regressions were blocked"
