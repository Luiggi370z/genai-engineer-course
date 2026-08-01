"""TODO: build one client that talks to any provider behind a single function.

Goal: complete(prompt, provider) works for "gpt", "claude", and "local" (Ollama),
and adding a new provider is a config change, not a new code path.

Fill in the TODOs. The tests in tests/test_client.py tell you the shape.
Reference: ../after/src/client.py (peek only when stuck).
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Provider:
    base_url: str | None
    api_key: str
    model: str


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


# TODO 1: fill in the provider registry. OpenAI-compatible endpoints (OpenAI,
# Ollama) should share one adapter — only base_url + model differ.
PROVIDERS: dict[str, Provider] = {
    # "gpt": Provider(None, _env("OPENAI_API_KEY"), "gpt-5.5"),
    # "local": Provider("http://localhost:11434/v1", "ollama", "qwen3.5:8b"),
}


def complete(prompt: str, provider: str = "local", temperature: float = 0.2) -> str:
    """TODO 2: dispatch to the right adapter and return the text response."""
    raise NotImplementedError("build the universal client")
