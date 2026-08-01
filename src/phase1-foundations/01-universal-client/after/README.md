# 1.1 Universal client — reference

`complete`, `stream`, `call_tool` and `extract` across five providers — OpenAI,
Anthropic, Google (via its OpenAI-compatible endpoint), Ollama and MLX — with tool
calls and structured output normalized to one shape each.

`make check` passes offline: the SDK clients are swapped for fakes, so the tests
verify the normalization, not the network. `make test-integration` runs the same
four calls against a real local model (needs Ollama serving `qwen3.5:9b`).
Try it live: `make setup && uv run python -m src.client`.
