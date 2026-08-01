"""Where the candidates are declared, and the one function that talks to a vendor.

Everything above this file is provider-agnostic. That is the whole point of the
adapter from lesson 01: the bench does not import `openai`, this module does.
"""
from __future__ import annotations

import os

from .core import Candidate, Reply

# Prices are $/MTok (input, output). Local models are free per token — the cost
# is your electricity and your patience, neither of which bills per request.
CANDIDATES: dict[str, Candidate] = {
    "local": Candidate("local", "qwen3.5:9b", price_in=0.0, price_out=0.0),
    "local-big": Candidate("local-big", "qwen3-coder:30b", price_in=0.0, price_out=0.0),
    "gpt": Candidate("gpt", "gpt-5.2", price_in=1.75, price_out=14.00),
    "gpt-mini": Candidate("gpt-mini", "gpt-5.4-mini", price_in=0.25, price_out=2.00),
}

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")


def resolve(names: list[str]) -> list[Candidate]:
    """Turn CLI names into candidates.

    TODO: raise `KeyError` naming the unknown entries and listing the valid ones.
    A typo that silently benches three providers instead of four is a bug you
    will not notice until the report looks oddly cheap.
    """
    raise NotImplementedError


def live_runner(candidate: Candidate, prompt: str) -> Reply:
    """One call over an OpenAI-compatible endpoint. Ollama and OpenAI both are.

    TODO: build an `OpenAI` client (local candidates point at `OLLAMA_BASE_URL`
    with any api_key; hosted ones use the environment), send the prompt at
    `temperature=0`, and return a `Reply` carrying the usage numbers off the
    response. Read `usage` — do not recount the prompt with tiktoken and call it
    cost. Cached input tokens, when the vendor reports them, live under
    `usage.prompt_tokens_details.cached_tokens`.
    """
    raise NotImplementedError
