"""The task under test: pull a typed invoice out of messy text.

This is lesson 03's schema, reused on purpose. The bench is not a new idea — it
is the three things you already built (an adapter, a meter, a schema) pointed at
each other so they produce a number you can defend in an interview.

The validator answers one narrow question: *did the reply parse into the shape?*
It deliberately does **not** ask whether the values are right. Schema validity is
a type check; accuracy is an eval, and evals are Phase 3. Conflating them is how
you end up shipping a model that returns a beautifully-typed zero.
"""
from __future__ import annotations

import json

from pydantic import BaseModel, Field, ValidationError


class Invoice(BaseModel):
    """Constraints live in the type, not in the prompt."""

    vendor: str = Field(min_length=1)
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    total: float = Field(ge=0)


PROMPT = """Extract the invoice fields from the text below.
Reply with JSON only: {{"vendor": str, "date": "YYYY-MM-DD", "total": number}}

TEXT:
{text}"""

# Messy on purpose: different orderings, currency symbols, spelled-out dates,
# a thousands separator. Every one of these has broken somebody's regex.
CASES: tuple[str, ...] = (
    "INVOICE — Northwind Traders\nDated 2026-03-04\nAmount due: $1,240.50",
    "Acme Corp\nTotal: EUR 89,99\nInvoice date: 12 January 2026",
    "Paid to Globex on 2026-11-30. Grand total 45 USD. Ref #A-2231",
    "Statement\nvendor.....: Initech\ndate.......: 2026/07/01\nbalance....: 0.00",
)


def prompts() -> list[str]:
    return [PROMPT.format(text=case) for case in CASES]


def validate_invoice(text: str) -> bool:
    """True when the reply is JSON that satisfies `Invoice`. Nothing more."""
    try:
        Invoice.model_validate(json.loads(strip_fence(text)))
    except (json.JSONDecodeError, ValidationError, TypeError):
        return False
    return True


def strip_fence(text: str) -> str:
    """Small models love a ```json fence. Peel it before parsing.

    Note what this is *not*: it is not parsing prose. If you find yourself adding
    a second cleanup rule here, that is the signal to turn on a real structured
    output mode instead (`p1-c-schema`), not to grow a parser.
    """
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    body = stripped.split("\n", 1)[-1]
    return body.rsplit("```", 1)[0].strip()
