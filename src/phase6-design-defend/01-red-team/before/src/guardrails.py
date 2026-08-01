"""TODO: build the layered guardrails.

- decode_and_normalize(text): undo base64 BEFORE scanning.
- spotlight(untrusted): wrap untrusted content as DATA, not instructions.
- layer1(text): (ok, cleaned/reason) — length cap, block obvious injection,
  redact PII.
- layer3_output_ok(answer, contexts): no PII leak + grounded in context.

Reference: ../after/src/guardrails.py.
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
    re.compile(r"reveal.{0,20}(system )?prompt", re.I),
    re.compile(r"forward .* to .*@", re.I),
]


def decode_and_normalize(text: str) -> str:
    raise NotImplementedError  # TODO 1


def spotlight(untrusted: str) -> str:
    raise NotImplementedError  # TODO 2


def layer1(text: str) -> tuple[bool, str]:
    raise NotImplementedError  # TODO 3


def layer3_output_ok(answer: str, contexts: list[str]) -> bool:
    raise NotImplementedError  # TODO 4
