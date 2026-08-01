"""Workshop 6 layer — harden the assistant. Containment, not wishful filtering.

L1 decode+scan+redact on every untrusted string (incl. fetched emails/news),
spotlight untrusted content, and an output gate. Combined with the agent's HITL
+ least-privilege tools, a landed injection still can't fire a gated tool.
"""
from __future__ import annotations

import re

PII = [re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")]
INJECTION = [
    re.compile(
        r"ignore\s+(all\s+|the\s+)?(previous|prior|above|earlier).{0,20}instructions?",
        re.I,
    ),
    re.compile(r"you are now|new system prompt|disregard", re.I),
    re.compile(r"forward .* to .*@", re.I),
    re.compile(r"reveal.{0,20}(system )?prompt", re.I),
]


def decode_and_normalize(text: str) -> str:
    raise NotImplementedError  # TODO
def spotlight(untrusted: str) -> str:
    raise NotImplementedError  # TODO
def screen(text: str) -> tuple[bool, str]:
    """L1: (ok, cleaned_or_reason). Blocks injection; redacts PII; caps length."""
    raise NotImplementedError  # TODO
def output_ok(answer: str) -> bool:
    """L3 output gate: never leak PII in a response."""
    raise NotImplementedError  # TODO
