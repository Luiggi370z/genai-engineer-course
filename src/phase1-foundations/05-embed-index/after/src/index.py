"""A mini vector store: embed chunks, index them in numpy, search by cosine.

Embeddings via a local model (nomic-embed-text through Ollama's OpenAI-compatible
endpoint). Normalize once at index time, then cosine = a single matrix-vector dot.
That IS a vector store, minus the ops.

The embedder is injected. Two payoffs: `search` can be tested offline against
vectors you chose, and swapping nomic-embed-text for BGE-M3 — or for Qdrant in
Phase 2 — is an argument rather than a rewrite.
"""
from __future__ import annotations

from collections.abc import Callable

import numpy as np

Embedder = Callable[[list[str]], np.ndarray]


def embed(texts: list[str], model: str = "nomic-embed-text") -> np.ndarray:
    """Embed a list of texts locally; return an L2-normalized (n, d) matrix."""
    from openai import OpenAI

    client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
    resp = client.embeddings.create(model=model, input=texts)
    vecs = np.array([d.embedding for d in resp.data], dtype=np.float32)
    return normalize(vecs)


def normalize(m: np.ndarray) -> np.ndarray:
    """L2-normalize rows, leaving zero rows alone instead of dividing by zero."""
    norms = np.linalg.norm(m, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return m / norms


class VectorIndex:
    """Hold normalized vectors + their source chunks; search by cosine top-k."""

    def __init__(
        self,
        chunks: list[str],
        matrix: np.ndarray,
        embedder: Embedder = embed,
    ) -> None:
        self.chunks = chunks
        self.matrix = matrix  # (n, d), already normalized
        self.embedder = embedder

    @classmethod
    def build(cls, chunks: list[str], embedder: Embedder = embed) -> VectorIndex:
        return cls(chunks, embedder(chunks), embedder)

    def search(self, query: str, k: int = 3) -> list[tuple[str, float]]:
        q = self.embedder([query])[0]  # (d,), normalized
        scores = self.matrix @ q  # cosine, because everything is normalized
        top = np.argsort(scores)[::-1][:k]
        return [(self.chunks[i], float(scores[i])) for i in top]


if __name__ == "__main__":
    idx = VectorIndex.build(["my card got declined", "payment failure", "great weather today"])
    # Different words, same meaning -> should still land on the payment chunks.
    for chunk, score in idx.search("the transaction did not go through", k=2):
        print(f"{score:.3f}  {chunk}")
