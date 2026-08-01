"""Offline tests: the schema AND the extraction path, both without a live model.

A fake extractor stands in for the Instructor-patched client. That is the only
reason `extract_all` and `violation_rate` can be tested at all — and it is the
reason this test file fails in `before/` until those functions exist.
"""
from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from src.extract import Invoice, extract_all, extract_invoice, violation_rate

GOOD = "Acme Corp billed us $4,231.50 on July 3rd 2026."
HOPELESS = "see attached"


class FakeExtractor:
    """Answers from a script; raises for the cases a small model would fumble."""

    def __init__(self, replies: dict[str, Invoice | Exception]) -> None:
        self.replies = replies
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Invoice:
        self.calls.append(kwargs)
        text = kwargs["messages"][0]["content"]
        reply = self.replies[text]
        if isinstance(reply, Exception):
            raise reply
        return reply


def test_invoice_schema_shape():
    inv = Invoice(vendor="Acme", date="2026-07-03", total=4231.50)
    assert inv.total == 4231.50
    assert inv.vendor == "Acme"


def test_invoice_rejects_bad_total():
    with pytest.raises(ValidationError):
        Invoice(vendor="Acme", date="2026-07-03", total="not a number")  # type: ignore[arg-type]


def test_invoice_rejects_a_negative_total():
    with pytest.raises(ValidationError):
        Invoice(vendor="Acme", date="2026-07-03", total=-1.0)


def test_extraction_asks_for_the_schema_not_for_json_in_prose():
    """The schema goes in `response_model`. If it only appears in the prompt, you
    have a suggestion rather than a constraint."""
    want = Invoice(vendor="Acme", date="2026-07-03", total=4231.50)
    fake = FakeExtractor({GOOD: want})
    got = extract_invoice(GOOD, client=fake)
    assert got == want
    assert fake.calls[0]["response_model"] is Invoice


def test_a_case_the_model_cannot_shape_is_counted_not_crashed():
    fake = FakeExtractor(
        {
            GOOD: Invoice(vendor="Acme", date="2026-07-03", total=4231.50),
            HOPELESS: ValueError("could not satisfy schema after retries"),
        }
    )
    invoices, violations = extract_all([GOOD, HOPELESS], client=fake)
    assert len(invoices) == 1
    assert len(violations) == 1
    assert violation_rate([GOOD, HOPELESS], violations) == 0.5


def test_violation_rate_is_zero_for_an_empty_run():
    assert violation_rate([], []) == 0.0


def test_a_clean_run_reports_no_violations():
    texts = [GOOD]
    fake = FakeExtractor({GOOD: Invoice(vendor="Acme", date="2026-07-03", total=1.0)})
    invoices, violations = extract_all(texts, client=fake)
    assert len(invoices) == 1
    assert violation_rate(texts, violations) == 0.0
