"""Workshop 2 layer — a small hybrid-retrieval RAG core the assistant can query.

Self-contained (offline) BM25 + bag-of-words dense, fused with RRF — the same
shape as phase2/02-hybrid-rerank, now a reusable component. Swap the store for
Qdrant + real embeddings in production; the interface stays put.
"""
from __future__ import annotations

import math
from collections import Counter


class RagStore:
    def __init__(self, docs: list[str]) -> None:
        self.docs = docs
        self.toks = [d.lower().split() for d in docs]
        self.df: Counter[str] = Counter()
        for t in self.toks:
            self.df.update(set(t))
        self.n = max(1, len(docs))
        self.avg = sum(len(t) for t in self.toks) / self.n

    def _bm25(self, q: list[str]) -> list[int]:
        out = []
        for i, toks in enumerate(self.toks):
            tf = Counter(toks)
            s = 0.0
            for term in q:
                if term not in tf:
                    continue
                idf = math.log(1 + (self.n - self.df[term] + 0.5) / (self.df[term] + 0.5))
                denom = tf[term] + 1.5 * (0.25 + 0.75 * len(toks) / self.avg)
                s += idf * (tf[term] * 2.5) / denom
            out.append((i, s))
        return [i for i, s in sorted(out, key=lambda x: -x[1]) if s > 0]

    def _dense(self, q: list[str]) -> list[int]:
        qc = Counter(q)
        out = []
        for i, toks in enumerate(self.toks):
            d = Counter(toks)
            dot = sum(qc[t] * d[t] for t in qc)
            norm = math.sqrt(sum(v * v for v in qc.values())) * math.sqrt(
                sum(v * v for v in d.values())
            )
            out.append((i, dot / norm if norm else 0.0))
        return [i for i, s in sorted(out, key=lambda x: -x[1]) if s > 0]

    def search(self, query: str, k: int = 3) -> list[str]:
        raise NotImplementedError  # TODO
