"""One tiny client that talks to any provider — hosted or local.

The whole point: provider choice is a config string, never a code change.
OpenAI-compatible endpoints (OpenAI, Ollama, MLX) share one adapter; only the
base_url and model differ. Anthropic gets a thin adapter with the same signature.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Provider:
    base_url: str | None  # None = the SDK's default (real OpenAI / Anthropic)
    api_key: str
    model: str


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


# Everything is config. Add a row, get a provider — no new code path.
PROVIDERS: dict[str, Provider] = {
    "gpt": Provider(None, _env("OPENAI_API_KEY"), "gpt-5.5"),
    "claude": Provider(None, _env("ANTHROPIC_API_KEY"), "claude-sonnet-4-6"),
    "local": Provider("http://localhost:11434/v1", "ollama", "qwen3.5:8b"),
}


def complete(prompt: str, provider: str = "local", temperature: float = 0.2) -> str:
    """Send one prompt, get the text back. Works for every provider above."""
    p = PROVIDERS[provider]
    if provider == "claude":
        return _complete_anthropic(p, prompt, temperature)
    return _complete_openai(p, prompt, temperature)


def _complete_openai(p: Provider, prompt: str, temperature: float) -> str:
    from openai import OpenAI

    client = OpenAI(base_url=p.base_url, api_key=p.api_key or "x")
    resp = client.chat.completions.create(
        model=p.model,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content or ""


def _complete_anthropic(p: Provider, prompt: str, temperature: float) -> str:
    from anthropic import Anthropic

    client = Anthropic(api_key=p.api_key)
    resp = client.messages.create(
        model=p.model,
        max_tokens=1024,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    # Anthropic returns a list of content blocks; concatenate the text ones.
    return "".join(b.text for b in resp.content if b.type == "text")


if __name__ == "__main__":
    print(complete("Say hi in five words.", provider="local"))
