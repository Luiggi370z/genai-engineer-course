"""TODO: build a mini vector store.

- normalize(m): L2-normalize rows — and leave a zero row alone rather than
  dividing by zero.
- embed(texts): local embeddings via Ollama (nomic-embed-text), normalized.
- VectorIndex.build(chunks, embedder): embed + hold vectors beside their chunks.
- VectorIndex.search(query, k): cosine top-k (normalized -> a single dot product).

Note the `embedder` parameter: `search` has to embed the query, and taking the
embedder as an argument is what makes that testable without a live model. The same
seam is how you swap nomic-embed-text for BGE-M3, or numpy for Qdrant in Phase 2.

Then try a query phrased with DIFFERENT words than the text and watch it hit;
try an exact ID and watch it MISS (remember that for Phase 2 — hybrid search).

Reference: ../after/src/index.py.
"""
from __future__ import annotations

from collections.abc import Callable

import numpy as np

Embedder = Callable[[list[str]], np.ndarray]


def normalize(m: np.ndarray) -> np.ndarray:
    """TODO 1: L2-normalize rows; a zero row must stay a zero row."""
    raise NotImplementedError


def embed(texts: list[str], model: str = "nomic-embed-text") -> np.ndarray:
    """TODO 2: embed locally through Ollama, return a normalized (n, d) matrix."""
    raise NotImplementedError


class VectorIndex:
    def __init__(
        self,
        chunks: list[str],
        matrix: np.ndarray,
        embedder: Embedder = embed,
    ) -> None:
        self.chunks = chunks
        self.matrix = matrix
        self.embedder = embedder

    @classmethod
    def build(cls, chunks: list[str], embedder: Embedder = embed) -> VectorIndex:
        """TODO 3: embed the chunks and keep row i aligned with chunk i."""
        raise NotImplementedError

    def search(self, query: str, k: int = 3) -> list[tuple[str, float]]:
        """TODO 4: embed the query, dot it against the matrix, return top-k.

        Because everything is normalized, the dot product *is* cosine similarity —
        no division, no loop over rows.
        """
        raise NotImplementedError
