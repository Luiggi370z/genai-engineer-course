"""Structured outputs: get a guaranteed shape back, not prose to regex.

Same code, hosted or local — Instructor wraps any OpenAI-compatible client and
forces the model to return an object matching your Pydantic schema.

The client is a parameter, not a global. That is what lets the offline tier test
the extraction path against a fake and the integration tier run the identical
code against a real model.
"""
from __future__ import annotations

from collections.abc import Sequence
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
    hit a 0% violation rate and still invent every total. That is what
    `field_accuracy` is for, and the gap between the two numbers is the whole
    finding of the shoot-out.
    """
    return len(violations) / len(texts) if texts else 0.0


def field_accuracy(
    got: Sequence[Invoice | None], expected: Sequence[Invoice]
) -> dict[str, float]:
    """Share correct per field — the other half of the shoot-out.

    The exercise asks you to compare a frontier model against the one on your
    laptop, and a violation rate cannot answer that: constrained decoding takes
    both to roughly zero, so the interesting difference lives entirely in whether
    the values are right. Per field rather than one average, because they fail
    differently — `vendor` is copied out of the text, `total` has to be read off
    the right line, and `date` has to be reformatted, which is where a small
    model loses. Averaging the three hides the one you would have tiered on.

    Totals compare within a cent: a float that came back from JSON is not going
    to be bit-identical, and treating `4231.5` and `4231.50` as different answers
    would measure the parser rather than the model.

    `got` is positional and may carry `None` where the provider produced nothing.
    A hole rather than a shorter list, because dropping the failures would slide
    every later answer onto the wrong expected row and score a model as wrong
    about invoices it read correctly.
    """
    fields = list(Invoice.model_fields)
    if not expected:
        return dict.fromkeys(fields, 0.0)
    scores = {}
    for field in fields:
        hits = sum(
            1
            for want, have in zip(expected, got, strict=False)
            if have is not None and _same(getattr(want, field), getattr(have, field))
        )
        scores[field] = hits / len(expected)
    return scores


def _same(want: Any, have: Any) -> bool:
    if isinstance(want, float) and isinstance(have, float):
        return abs(want - have) < 0.01
    return str(want).strip().casefold() == str(have).strip().casefold()


def compare_providers(
    texts: list[str],
    expected: list[Invoice],
    clients: dict[str, Extractor],
    model: str = "qwen3.5:9b",
) -> dict[str, dict[str, float]]:
    """One row per provider: violation rate, then accuracy per field.

    Parameterized by client rather than by provider name so the offline tier can
    run the identical comparison against fakes — the shoot-out is a measurement
    procedure, and a procedure you can only run with two API keys is one you
    cannot test. Point it at `build_client("gpt")` and `build_client("local")`
    and it is the exercise.
    """
    rows = {}
    for name, client in clients.items():
        got: list[Invoice | None] = []
        violations: list[str] = []
        for text in texts:
            try:
                got.append(extract_invoice(text, client, model=model))
            except (ValidationError, ValueError) as exc:
                got.append(None)
                violations.append(f"{text[:40]}… → {type(exc).__name__}")
        rows[name] = {
            "violation_rate": violation_rate(texts, violations),
            **field_accuracy(got, expected),
        }
    return rows


if __name__ == "__main__":
    inv = extract_invoice("Acme Corp billed us $4,231.50 on July 3rd 2026.")
    print(inv.model_dump())
