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
    # multilingual override + exfiltration verbs — see phase6 red-team v2
    re.compile(
        r"(ignora|ignorez|ignoriere|ignore)\b.{0,40}"
        r"(instrucciones|instructions|anweisungen|instru\u00e7\u00f5es)",
        re.I,
    ),
    re.compile(r"(send|forward|email|upload|export)\b.{0,60}\bto\b.{0,40}@", re.I),
    re.compile(r"(upload|post|send)\b.{0,60}https?://", re.I),
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
