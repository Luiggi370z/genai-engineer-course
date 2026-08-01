"""Real adapters — the production tier. Each one has the same shape as the offline
component it replaces, so `service.py` picks between them by settings and nothing
else changes. Heavy libraries (qdrant-client, ollama, mcp) are imported lazily
INSIDE the adapter, so importing this module costs nothing and the fast tier never
drags them in.

- InMemoryRag / QdrantStore : both expose add(docs) + search(query, k) -> list[str]
- ollama_generate           : a text-completion call against a local model
- mcp_tools                 : discover + invoke tools on a real MCP server (mcp SDK)
"""
from __future__ import annotations

import hashlib
from collections.abc import Callable
from typing import Any

from assistant.rag import RagStore

# --- RAG: offline default and the Qdrant tier, one interface --------------------


class InMemoryRag:
    """Offline store with an add() the immutable RagStore lacks. Rebuilds the BM25
    index on ingest — fine at workshop corpus sizes, and it keeps search() honest."""

    def __init__(self, docs: list[str] | None = None) -> None:
        self._docs: list[str] = list(docs or [])
        self._store = RagStore(self._docs)

    def add(self, docs: list[str]) -> int:
        self._docs.extend(docs)
        self._store = RagStore(self._docs)
        return len(docs)

    def search(self, query: str, k: int = 3) -> list[str]:
        return self._store.search(query, k) if self._docs else []


def hash_embed(text: str, dim: int = 64) -> list[float]:
    """Deterministic bag-of-words vector. Not semantic — its job is to prove the
    Qdrant round-trip (upsert + filtered query) without pulling an embedding model
    into the test. Swap for nomic-embed-text in a deployment that needs recall."""
    vec = [0.0] * dim
    for token in text.lower().split():
        h = int(hashlib.sha1(token.encode()).hexdigest(), 16)
        vec[h % dim] += 1.0
    norm = sum(v * v for v in vec) ** 0.5
    return [v / norm for v in vec] if norm else vec


class QdrantStore:
    """RagStore's interface, backed by a real Qdrant collection."""

    def __init__(
        self,
        url: str,
        collection: str = "assistant",
        embed: Callable[[str], list[float]] = hash_embed,
        dim: int = 64,
    ) -> None:
        from qdrant_client import QdrantClient  # lazy: only when the real tier is on
        from qdrant_client.models import Distance, VectorParams

        self.client = QdrantClient(url=url)
        self.collection = collection
        self.embed = embed
        self._id = 0
        if not self.client.collection_exists(collection):
            self.client.create_collection(
                collection, vectors_config=VectorParams(size=dim, distance=Distance.COSINE)
            )

    def add(self, docs: list[str]) -> int:
        from qdrant_client.models import PointStruct

        points = []
        for doc in docs:
            self._id += 1
            points.append(
                PointStruct(id=self._id, vector=self.embed(doc), payload={"text": doc})
            )
        if points:
            self.client.upsert(self.collection, points=points)
        return len(points)

    def search(self, query: str, k: int = 3) -> list[str]:
        hits = self.client.query_points(
            self.collection, query=self.embed(query), limit=k
        ).points
        return [h.payload["text"] for h in hits if h.payload]


# --- generation: the Ollama tier -----------------------------------------------


def ollama_generate(prompt: str, *, host: str, model: str) -> str:
    """One non-streaming completion against a local Ollama model."""
    from ollama import Client  # lazy

    response = Client(host=host).generate(model=model, prompt=prompt)
    return response["response"].strip()


# --- tools: discover + invoke on a real MCP server ------------------------------


def mcp_tools(target: Any) -> tuple[list[dict], Callable[[str, dict], Any]]:
    """List a real MCP server's tools and return (specs, invoker) shaped exactly for
    `mcp_client.extend_assistant`. `target` is anything the v2 SDK's Client accepts:
    a URL string (streamable HTTP) in production, or an MCPServer instance in-memory.

    This is the real replacement for the injected-dict fake in mcp_client.py: the
    specs come from the server at runtime, so adding a tool server-side and
    restarting is all it takes for the assistant to gain it.
    """
    import asyncio

    import anyio
    from mcp import Client

    def run_sync(async_fn: Callable) -> Any:
        """anyio.run, unless this thread already hosts a loop — uvicorn's --factory
        loads the app INSIDE its event loop, so discovery at boot must hop to a
        fresh thread rather than nest a second loop in this one."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return anyio.run(async_fn)
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(anyio.run, async_fn).result()

    async def _list() -> list[dict]:
        async with Client(target) as client:
            listed = await client.list_tools()
            return [
                {"name": t.name, "description": t.description or ""} for t in listed.tools
            ]

    def invoker(name: str, args: dict) -> Any:
        async def _call() -> Any:
            async with Client(target) as client:
                result = await client.call_tool(name, args)
                return [getattr(c, "text", str(c)) for c in result.content]

        return run_sync(_call)

    return run_sync(_list), invoker
