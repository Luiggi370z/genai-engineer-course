"""TODO: implement two splitters and a worst-chunk inspector.

- fixed_size(text, size, overlap): word windows WITH overlap.
- heading_aware(text, max_words): split on markdown headings, then size-cap.
- worst_chunk(chunks): return the chunk that makes least sense alone
  (proxy: the shortest non-empty one).

Reference: ../after/src/chunk.py.
"""
from __future__ import annotations


def fixed_size(text: str, size: int = 512, overlap: int = 75) -> list[str]:
    raise NotImplementedError  # TODO 1


def heading_aware(text: str, max_words: int = 512) -> list[str]:
    raise NotImplementedError  # TODO 2


def worst_chunk(chunks: list[str]) -> str:
    raise NotImplementedError  # TODO 3
