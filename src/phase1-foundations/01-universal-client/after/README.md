# 1.1 Universal client — reference

Working `complete(prompt, provider)` across OpenAI-compatible endpoints (OpenAI,
Ollama) and Anthropic. `make check` passes offline (tests verify the abstraction,
not the network). Try it live: `make setup && uv run python -m src.client`.
