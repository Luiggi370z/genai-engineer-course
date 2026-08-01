include ../../../_lesson.mk

# The gate itself, runnable exactly the way CI runs it.
.PHONY: gate
gate:             ## fail the build on a regression (no model needed)
	uv run python -m src.gate evals/results.json evals/baseline.json
