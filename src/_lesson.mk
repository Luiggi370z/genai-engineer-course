# Shared lesson targets. Each lesson's Makefile does:  include ../../_lesson.mk
.PHONY: setup lint type test check clean
setup:            ## create venv + install deps
	uv sync
lint:             ## ruff check
	uv run ruff check .
type:             ## pyright
	uv run pyright
test:             ## pytest (fast, offline)
	uv run pytest -q -m "not integration"
check: lint type test   ## everything CI runs
clean:
	rm -rf .venv .ruff_cache .pytest_cache **/__pycache__

# Opt-in tier: real models / real services (downloads weights, needs Ollama, etc.)
.PHONY: test-integration
test-integration:
	uv run --group integration pytest -q -m integration
