"""Structured outputs: get a guaranteed shape back, not prose to regex.

Same code, hosted or local — Instructor wraps any OpenAI-compatible client and
forces the model to return an object matching your Pydantic schema.

The client is a parameter, not a global. That is what lets the offline tier test
the extraction path against a fake and the integration tier run the identical
code against a real model.
"""
from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field, ValidationError


class Invoice(BaseModel):
    vendor: str = Field(min_length=1)
    date: str = Field(description="ISO date, e.g. 2026-07-16")
    total: float = Field(ge=0)


class Extractor(Protocol):
    """The one method Instructor-patched clients expose that we depend on."""

    def create(self, **kwargs: Any) -> Any: ...


def build_client(provider: str = "local") -> Extractor:
    """Return an Instructor-patched client. 'local' = Ollama, 'gpt' = OpenAI."""
    import instructor
    from openai import OpenAI

    if provider == "local":
        base = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
        patched = instructor.from_openai(base, mode=instructor.Mode.JSON)
    else:
        patched = instructor.from_openai(OpenAI())
    return patched.chat.completions


def extract_invoice(
    text: str,
    client: Extractor | None = None,
    provider: str = "local",
    model: str = "qwen3.5:9b",
) -> Invoice:
    """Pull a typed Invoice out of messy text. No regex, guaranteed schema."""
    extractor = client or build_client(provider)
    return extractor.create(
        model=model,
        response_model=Invoice,
        messages=[{"role": "user", "content": text}],
    )


def extract_all(
    texts: list[str],
    client: Extractor | None = None,
    provider: str = "local",
    model: str = "qwen3.5:9b",
) -> tuple[list[Invoice], list[str]]:
    """The shoot-out's measuring stick: what parsed, and what refused to.

    Returns (invoices, violations). A violation is a case where even constrained
    decoding plus Instructor's retries could not produce the shape — which is the
    rate you compare between a frontier model and the one on your laptop.
    """
    invoices: list[Invoice] = []
    violations: list[str] = []
    for text in texts:
        try:
            invoices.append(extract_invoice(text, client, provider, model))
        except (ValidationError, ValueError) as exc:
            violations.append(f"{text[:40]}… → {type(exc).__name__}")
    return invoices, violations


def violation_rate(texts: list[str], violations: list[str]) -> float:
    """Share of cases that never produced a valid object. Lower is better.

    Note what this does *not* measure: whether the fields are right. A model can
    hit a 0% violation rate and still invent every total. That gap is why Phase 3
    exists — validity is a type check, accuracy is an eval.
    """
    return len(violations) / len(texts) if texts else 0.0


if __name__ == "__main__":
    inv = extract_invoice("Acme Corp billed us $4,231.50 on July 3rd 2026.")
    print(inv.model_dump())
