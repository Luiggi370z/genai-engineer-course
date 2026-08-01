"""TODO: extract a typed Invoice from messy text using structured outputs.

1) build_client(provider): Instructor-wrap an OpenAI-compatible client
   ('local' -> Ollama JSON mode; 'gpt' -> OpenAI) and return its
   `.chat.completions`.
2) extract_invoice(text, client): return an Invoice via response_model — no regex.
   Take the client as a parameter so this is testable without a live model.
3) extract_all / violation_rate: run a batch and report what refused to parse.
   That rate is the number the shoot-out compares, hosted vs. laptop.

The Invoice model is given. Note the constraints live in the type (`min_length`,
`ge`) rather than in the prompt — on a strict provider the decoder enforces them.

Reference: ../after/src/extract.py.
"""
from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field


class Invoice(BaseModel):
    vendor: str = Field(min_length=1)
    date: str = Field(description="ISO date, e.g. 2026-07-16")
    total: float = Field(ge=0)


class Extractor(Protocol):
    """The one method Instructor-patched clients expose that we depend on."""

    def create(self, **kwargs: Any) -> Any: ...


def build_client(provider: str = "local") -> Extractor:
    """TODO 1: return an Instructor-patched client's `.chat.completions`."""
    raise NotImplementedError


def extract_invoice(
    text: str,
    client: Extractor | None = None,
    provider: str = "local",
    model: str = "qwen3.5:8b",
) -> Invoice:
    """TODO 2: pass `response_model=Invoice` so the shape is guaranteed.

    Putting "reply with JSON" in the prompt is a request; `response_model` is a
    constraint. Only one of them survives a model in a bad mood.
    """
    raise NotImplementedError


def extract_all(
    texts: list[str],
    client: Extractor | None = None,
    provider: str = "local",
    model: str = "qwen3.5:8b",
) -> tuple[list[Invoice], list[str]]:
    """TODO 3: return (invoices, violations).

    A case that cannot be shaped even after retries is a *data point*, not an
    exception to let escape — you are measuring a rate here.
    """
    raise NotImplementedError


def violation_rate(texts: list[str], violations: list[str]) -> float:
    """TODO 4: share of cases that never produced a valid object.

    Careful what you claim from this number: it says nothing about whether the
    fields are correct. A model can score 0% violations and invent every total.
    """
    raise NotImplementedError
