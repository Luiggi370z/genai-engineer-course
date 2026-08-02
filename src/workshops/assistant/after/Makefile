include ../../../_lesson.mk

.PHONY: report
report:           ## generate PORTFOLIO.md — eval scores, red-team results, latency, cost, decisions
	PYTHONPATH=src uv run python -m assistant.report
