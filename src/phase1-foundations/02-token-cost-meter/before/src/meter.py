"""TODO: build a cost meter — count before, measure after.

- count_openai(text): pre-flight token count with tiktoken (o200k_base).
- cost(model, usage): dollars from the usage object, accounting for CACHED tokens
  (~10% price) and remembering output tokens cost more than input.

Fill the TODOs; tests in tests/test_meter.py define the behavior.
Reference: ../after/src/meter.py.
"""
from __future__ import annotations

from dataclasses import dataclass

PRICE: dict[str, tuple[float, float]] = {
    "claude-sonnet-4-6": (3.00, 15.00),
    "gpt-5.5": (5.00, 30.00),
}


@dataclass
class Usage:
    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int = 0


def count_openai(text: str, model: str = "gpt-5.5") -> int:
    """TODO 1: return the tiktoken o200k_base token count for `text`."""
    raise NotImplementedError


def cost(model: str, usage: Usage) -> float:
    """TODO 2: compute dollars from the usage object. Cached input ~10% price."""
    raise NotImplementedError
