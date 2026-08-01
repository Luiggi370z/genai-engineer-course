"""Two splitters and a way to see the difference.

- fixed_size: the boring, reliable default (~size tokens, with overlap).
- heading_aware: split on markdown headings first, then size-cap each section.

Every chunker trades one failure for another; that's why Phase 2 MEASURES
instead of guessing. Here we just build both and eyeball the worst chunk.
"""
from __future__ import annotations

import re


def fixed_size(text: str, size: int = 512, overlap: int = 75) -> list[str]:
    """Word-based fixed windows with overlap (overlap keeps facts from splitting)."""
    words = text.split()
    step = size - overlap
    out: list[str] = []
    i = 0
    while i < len(words):
        out.append(" ".join(words[i : i + size]))
        i += step
    return out


def heading_aware(text: str, max_words: int = 512) -> list[str]:
    """Split on markdown headings, then size-cap any section that's too long."""
    # Split keeping the heading with its section.
    parts = re.split(r"(?m)^(#{1,6} .*)$", text)
    sections: list[str] = []
    buf = ""
    for p in parts:
        if re.match(r"^#{1,6} ", p):  # a heading starts a new section
            if buf.strip():
                sections.append(buf.strip())
            buf = p + "\n"
        else:
            buf += p
    if buf.strip():
        sections.append(buf.strip())
    # Size-cap each section using the fixed splitter.
    capped: list[str] = []
    for s in sections:
        if len(s.split()) <= max_words:
            capped.append(s)
        else:
            capped.extend(fixed_size(s, size=max_words, overlap=50))
    return capped


def worst_chunk(chunks: list[str]) -> str:
    """A cheap proxy for 'makes least sense alone': the shortest non-empty chunk."""
    return min((c for c in chunks if c.strip()), key=lambda c: len(c.split()), default="")


if __name__ == "__main__":
    doc = "# Intro\nHello world. " * 50 + "\n# Details\nMore text here. " * 50
    print("fixed:", len(fixed_size(doc)), "chunks")
    print("heading:", len(heading_aware(doc)), "chunks")
