# 8.1 Compose — reference

One `docker compose up --build` brings the real stack online: the capstone assistant and its MCP server (both built from the SAME image — `workshops/assistant/after` and its Dockerfile), plus pinned Qdrant and Ollama. Zero API keys.

What makes this deployable rather than a diagram:

- **Pinned images.** `qdrant/qdrant:v1.18.3`, `ollama/ollama:0.32.5`. `:latest` means every reviewer runs a different stack.
- **Healthchecks everywhere, and dependencies wait on them.** `depends_on: condition: service_healthy` — a started Qdrant is not a ready Qdrant.
- **Model bootstrap.** The ollama service pulls `qwen3.5:9b` and `nomic-embed-text` on first boot and only reports healthy once they're in, so the assistant never starts against an empty model store.
- **One published port.** Only the assistant reaches the host; MCP, Qdrant and Ollama stay on the compose network.

`src/health.py` reviews the compose file structurally (parsed YAML — services, pins, healthchecks, dependency conditions, published ports), and the tests prove the checks catch a broken file, not just bless this one.
