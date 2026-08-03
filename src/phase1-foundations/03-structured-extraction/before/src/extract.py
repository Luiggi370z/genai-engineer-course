"""TODO: extract a typed Invoice from messy text using structured outputs.

1) build_client(provider): Instructor-wrap an OpenAI-compatible client
   ('local' -> Ollama JSON mode; 'gpt' -> OpenAI) and return its
   `.chat.completions`.
2) extract_invoice(text, client): return an Invoice via response_model — no regex.
   Take the client as a parameter so this is testable without a live model.
3) extract_all / violation_rate: run a batch and report what refused to parse.
4) field_accuracy / compare_providers: whether the values are RIGHT, per field,
   for each provider. The violation rate alone cannot decide the shoot-out —
   constrained decoding takes every provider to roughly zero, so the difference
   you would tier a model on lives entirely in the accuracy columns.

The Invoice model is given. Note the constraints live in the type (`min_length`,
`ge`) rather than in the prompt — on a strict provider the decoder enforces them.

Reference: ../after/src/extract.py.
"""
from __future__ import annotations

from collections.abc import Sequence
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
    model: str = "qwen3.5:9b",
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
    model: str = "qwen3.5:9b",
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


def field_accuracy(
    got: Sequence[Invoice | None], expected: Sequence[Invoice]
) -> dict[str, float]:
    """TODO 5: share correct per field — the other half of the shoot-out.

    One entry per field of `Invoice`, not one average: they fail differently.
    `vendor` is copied out of the text, `total` has to be read off the right
    line, and `date` has to be reformatted, which is where a small model loses.
    An average hides the column you would have tiered on.

    Compare totals within a cent. A float that came back through JSON will not be
    bit-identical, and scoring `4231.5` against `4231.50` as a miss measures the
    parser rather than the model. Everything else compares case-insensitively
    after a strip. No expected rows means no evidence: return zeros, not a
    division by zero and not a cheerful 1.0.

    `got` is positional and carries `None` where the provider produced nothing —
    score those as misses. A shorter list instead of a hole would slide every
    later answer onto the wrong expected row and mark a model wrong about
    invoices it read correctly.
    """
    raise NotImplementedError


def compare_providers(
    texts: list[str],
    expected: list[Invoice],
    clients: dict[str, Extractor],
    model: str = "qwen3.5:9b",
) -> dict[str, dict[str, float]]:
    """TODO 6: one row per provider — `violation_rate`, then the accuracy fields.

    Take the clients as a dict rather than provider names, so the same procedure
    runs against fakes offline and against `build_client("gpt")` /
    `build_client("local")` for the real shoot-out. A comparison you can only run
    with two API keys is one you cannot test, and an untested comparison is how a
    tiering decision ends up resting on a number nobody re-derived.

    Extract one text at a time and append `None` for the ones that raise, so the
    answers stay lined up with `expected`; `extract_all`'s shorter list is the
    right shape for a rate and the wrong one for an accuracy.
    """
    raise NotImplementedError
