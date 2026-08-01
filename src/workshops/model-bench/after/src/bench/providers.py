"""Where the candidates are declared, and the one function that talks to a vendor.

Everything above this file is provider-agnostic. That is the whole point of the
adapter from lesson 01: the bench does not import `openai`, `providers` does.
"""
from __future__ import annotations

import os

from .core import Candidate, Reply, Usage

# Prices are $/MTok (input, output). Local models are free per token — the cost
# is your electricity and your patience, neither of which bills per request.
CANDIDATES: dict[str, Candidate] = {
    "local": Candidate("local", "qwen3.5:8b", price_in=0.0, price_out=0.0),
    "local-big": Candidate("local-big", "qwen3-coder:30b", price_in=0.0, price_out=0.0),
    "gpt": Candidate("gpt", "gpt-5.2", price_in=1.75, price_out=14.00),
    "gpt-mini": Candidate("gpt-mini", "gpt-5.4-mini", price_in=0.25, price_out=2.00),
}

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")


def resolve(names: list[str]) -> list[Candidate]:
    """Turn CLI names into candidates, failing loudly on a typo."""
    unknown = [n for n in names if n not in CANDIDATES]
    if unknown:
        raise KeyError(f"unknown candidate(s): {', '.join(unknown)} — pick from {list(CANDIDATES)}")
    return [CANDIDATES[n] for n in names]


def live_runner(candidate: Candidate, prompt: str) -> Reply:
    """One call over an OpenAI-compatible endpoint. Ollama and OpenAI both are.

    `usage` comes straight off the response. If a vendor ever omits it, the bench
    should report a zero cost rather than invent one — an estimate in a cost
    report is worse than a blank, because a blank is visibly missing.
    """
    from openai import OpenAI

    local = candidate.name.startswith("local")
    client = OpenAI(
        base_url=OLLAMA_BASE_URL if local else None,
        api_key="ollama" if local else os.environ.get("OPENAI_API_KEY", ""),
    )
    resp = client.chat.completions.create(
        model=candidate.model,
        temperature=0,  # extraction: no creativity wanted
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    usage = resp.usage
    cached = 0
    if usage is not None and usage.prompt_tokens_details is not None:
        cached = usage.prompt_tokens_details.cached_tokens or 0
    return Reply(
        text=resp.choices[0].message.content or "",
        usage=Usage(
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            cache_read_input_tokens=cached,
        ),
    )
