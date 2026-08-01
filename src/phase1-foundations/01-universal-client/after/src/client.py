"""One tiny client that talks to any provider — hosted or local.

The whole point: provider choice is a config string, never a code change.
OpenAI-compatible endpoints (OpenAI, Google's Gemini endpoint, Ollama, MLX)
share one adapter; only the base_url and model differ. Anthropic gets a thin
adapter behind the same signatures.

Four capabilities, one call each, every provider normalized to the same shape:

    complete(prompt)          -> str              one prompt, text back
    stream(prompt)            -> Iterator[str]    text deltas as they arrive
    call_tool(prompt, tools)  -> ToolCall | str   the model picks; YOU run it
    extract(prompt, schema)   -> dict             schema-valid JSON, checked

The SDK clients are built by `_openai_client` / `_anthropic_client` so tests can
swap in fakes — the normalization logic is what this lesson tests, offline.
"""
from __future__ import annotations

import json
import os
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Provider:
    base_url: str | None  # None = the SDK's default (real OpenAI / Anthropic)
    api_key: str
    model: str


@dataclass(frozen=True)
class ToolCall:
    """A normalized tool request. Same shape whichever provider produced it."""

    name: str
    args: dict[str, Any]


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


# Everything is config. Add a row, get a provider — no new code path. Google's
# Gemini API speaks the OpenAI wire format at this base_url, which is why a
# fourth provider costs one line and zero new adapters.
PROVIDERS: dict[str, Provider] = {
    "gpt": Provider(None, _env("OPENAI_API_KEY"), "gpt-5.5"),
    "claude": Provider(None, _env("ANTHROPIC_API_KEY"), "claude-sonnet-4-6"),
    "gemini": Provider(
        "https://generativelanguage.googleapis.com/v1beta/openai/",
        _env("GOOGLE_API_KEY"),
        "gemini-2.5-flash",
    ),
    "local": Provider("http://localhost:11434/v1", "ollama", "qwen3.5:9b"),
    "mlx": Provider("http://localhost:8080/v1", "mlx", "mlx-community/Qwen3.5-9B-4bit"),
}


def _openai_client(p: Provider) -> Any:
    from openai import OpenAI

    return OpenAI(base_url=p.base_url, api_key=p.api_key or "x")


def _anthropic_client(p: Provider) -> Any:
    from anthropic import Anthropic

    return Anthropic(api_key=p.api_key)


# --- complete: one prompt, text back --------------------------------------


def complete(prompt: str, provider: str = "local", temperature: float = 0.2) -> str:
    """Send one prompt, get the text back. Works for every provider above."""
    p = PROVIDERS[provider]
    if provider == "claude":
        resp = _anthropic_client(p).messages.create(
            model=p.model,
            max_tokens=1024,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        # Anthropic returns a list of content blocks; concatenate the text ones.
        return "".join(b.text for b in resp.content if b.type == "text")
    resp = _openai_client(p).chat.completions.create(
        model=p.model,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content or ""


# --- stream: text deltas as they arrive ------------------------------------


def stream(prompt: str, provider: str = "local", temperature: float = 0.2) -> Iterator[str]:
    """Yield text deltas. ''.join(stream(...)) == complete(...), modulo sampling."""
    p = PROVIDERS[provider]
    if provider == "claude":
        with _anthropic_client(p).messages.stream(
            model=p.model,
            max_tokens=1024,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        ) as s:
            yield from s.text_stream
        return
    chunks = _openai_client(p).chat.completions.create(
        model=p.model,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )
    for chunk in chunks:
        # Some chunks carry no choices (usage frames) and some deltas are None.
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


# --- call_tool: the model picks a tool; you run it --------------------------
#
# Tools are declared once, provider-neutrally:
#   {"name": ..., "description": ..., "parameters": {<JSON schema>}}
# and adapted to each wire format here — the callers never see the difference.


def call_tool(
    prompt: str,
    tools: list[dict[str, Any]],
    provider: str = "local",
    temperature: float = 0.2,
) -> ToolCall | str:
    """Offer the model some tools. Returns a normalized ToolCall if it picked
    one, or the plain text answer if it didn't. Executing the tool is YOUR job —
    a client that auto-runs model-chosen code has skipped Phase 4 entirely."""
    p = PROVIDERS[provider]
    if provider == "claude":
        resp = _anthropic_client(p).messages.create(
            model=p.model,
            max_tokens=1024,
            temperature=temperature,
            tools=[
                {
                    "name": t["name"],
                    "description": t["description"],
                    "input_schema": t["parameters"],
                }
                for t in tools
            ],
            messages=[{"role": "user", "content": prompt}],
        )
        for block in resp.content:
            if block.type == "tool_use":
                return ToolCall(name=block.name, args=dict(block.input))
        return "".join(b.text for b in resp.content if b.type == "text")
    resp = _openai_client(p).chat.completions.create(
        model=p.model,
        temperature=temperature,
        tools=[{"type": "function", "function": t} for t in tools],
        messages=[{"role": "user", "content": prompt}],
    )
    message = resp.choices[0].message
    if message.tool_calls:
        call = message.tool_calls[0]
        return ToolCall(name=call.function.name, args=json.loads(call.function.arguments))
    return message.content or ""


# --- extract: schema-valid JSON, checked ------------------------------------


def extract(
    prompt: str,
    schema: dict[str, Any],
    provider: str = "local",
    temperature: float = 0.0,
) -> dict[str, Any]:
    """Structured output: hand over a JSON schema, get a dict back — and refuse
    a reply that is missing required fields rather than passing it downstream."""
    p = PROVIDERS[provider]
    if provider == "claude":
        # Anthropic's structured-output idiom: one forced tool whose input IS the schema.
        resp = _anthropic_client(p).messages.create(
            model=p.model,
            max_tokens=1024,
            temperature=temperature,
            tools=[
                {"name": "extract", "description": "Return the extraction.", "input_schema": schema}
            ],
            tool_choice={"type": "tool", "name": "extract"},
            messages=[{"role": "user", "content": prompt}],
        )
        data = next(dict(b.input) for b in resp.content if b.type == "tool_use")
    else:
        resp = _openai_client(p).chat.completions.create(
            model=p.model,
            temperature=temperature,
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "extraction", "schema": schema},
            },
            messages=[{"role": "user", "content": prompt}],
        )
        data = json.loads(resp.choices[0].message.content or "{}")
    missing = [key for key in schema.get("required", []) if key not in data]
    if missing:
        raise ValueError(f"model reply is missing required fields: {missing}")
    return data


if __name__ == "__main__":
    for delta in stream("Say hi in five words.", provider="local"):
        print(delta, end="", flush=True)
    print()
