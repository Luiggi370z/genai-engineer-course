"""Count before you send, measure after you get the bill.

2026 practice:
- BEFORE: use each vendor's own counter. Anthropic has a free count_tokens
  endpoint; OpenAI uses the local tiktoken library (o200k_base for GPT-4o/5.x).
  tiktoken UNDERCOUNTS Claude by ~15-20%, so never use it for Anthropic.
- AFTER: the response's `usage` object is the billing truth — input, output,
  cached (much cheaper), and reasoning tokens (billed as output).
"""
from __future__ import annotations

from dataclasses import dataclass

# $ per million tokens: (input, output). Keep prices in config next to models.
PRICE: dict[str, tuple[float, float]] = {
    "claude-sonnet-4-6": (3.00, 15.00),
    "gpt-5.5": (5.00, 30.00),
    "claude-opus-4-8": (5.00, 25.00),
}


@dataclass
class Usage:
    """A vendor-agnostic view of what a response actually cost, in tokens."""

    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int = 0  # cached input, ~90% cheaper when it hits


def count_openai(text: str, model: str = "gpt-5.5") -> int:
    """Pre-flight count for OpenAI models using the local tiktoken library."""
    import tiktoken

    enc = tiktoken.get_encoding("o200k_base")  # GPT-4o / 5.x encoding
    return len(enc.encode(text))


def cost(model: str, usage: Usage) -> float:
    """Dollars for one call, computed from the usage object (the billing truth)."""
    p_in, p_out = PRICE[model]
    cached = usage.cache_read_input_tokens
    fresh = usage.input_tokens - cached
    dollars = (
        fresh * p_in
        + cached * p_in * 0.1  # cached input ~10% of the price
        + usage.output_tokens * p_out  # reasoning tokens are billed here too
    ) / 1_000_000
    return dollars


if __name__ == "__main__":
    n = count_openai("The taxi meter is always running.")
    print(f"pre-flight tiktoken count: {n} tokens")
    demo = Usage(input_tokens=1000, output_tokens=500, cache_read_input_tokens=800)
    print(f"this call cost: ${cost('claude-sonnet-4-6', demo):.6f}")
