"""Real adapters — the production tier. Each one has the same shape as the offline
component it replaces, so `service.py` picks between them by settings and nothing
else changes. Heavy libraries (qdrant-client, ollama, mcp) are imported lazily
INSIDE the adapter, so importing this module costs nothing and the fast tier never
drags them in.

- InMemoryRag / QdrantStore : add(docs) + search(query, k) -> list[Chunk], plus
                              get(chunk_id) and delete(source) — a store you can
                              only write to is a store you cannot operate
- hash_embed / ollama_embed : the offline default and the real tier, one env var apart
- ollama_generate           : a text-completion call against a local model
- mcp_tools                 : discover + invoke tools on a real MCP server (mcp SDK)
"""
from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterator
from typing import Any

from assistant import resilience
from assistant.rag import Chunk, RagStore, as_chunks

# --- RAG: offline default and the Qdrant tier, one interface --------------------


DEFAULT_TENANT = "local"


class InMemoryRag:
    """Offline store with an add() the immutable RagStore lacks. Rebuilds the BM25
    index on ingest — fine at workshop corpus sizes, and it keeps search() honest.

    Documents are partitioned by TENANT (the caller's verified identity): what
    alice ingested can never surface in bob's retrieval, because bob's search
    only ever touches bob's index.

    Chunks are held in a dict keyed by chunk id, so re-adding a source overwrites
    its slices instead of stacking a second copy beside them — the same
    upsert-by-stable-id contract the Qdrant tier has, because a store whose
    duplicate behaviour changes with the tier is a store you cannot test."""

    def __init__(self, docs: list[str] | None = None) -> None:
        self._chunks: dict[str, dict[str, Chunk]] = {}
        self._stores: dict[str, RagStore] = {}
        if docs:
            self.add(docs)

    def _reindex(self, tenant: str) -> None:
        self._stores[tenant] = RagStore(list(self._chunks.get(tenant, {}).values()))

    def add(self, docs: list, tenant: str = DEFAULT_TENANT) -> int:
        chunks = as_chunks(docs, tenant)
        rows = self._chunks.setdefault(tenant, {})
        for chunk in chunks:
            rows[chunk.id] = chunk
        self._reindex(tenant)
        return len(chunks)

    def delete(self, source: str, tenant: str = DEFAULT_TENANT) -> int:
        """Forget one source entirely. A corpus you cannot delete from is a
        corpus that will eventually hold something you are not allowed to keep."""
        rows = self._chunks.get(tenant, {})
        doomed = [cid for cid, chunk in rows.items() if chunk.source == source]
        for cid in doomed:
            del rows[cid]
        self._reindex(tenant)
        return len(doomed)

    def get(self, chunk_id: str, tenant: str = DEFAULT_TENANT) -> Chunk | None:
        """Resolve a citation back to its evidence."""
        return self._chunks.get(tenant, {}).get(chunk_id)

    def search(self, query: str, k: int = 3, tenant: str = DEFAULT_TENANT) -> list[Chunk]:
        store = self._stores.get(tenant)
        return store.retrieve(query, k) if store else []


HASH_DIM = 64


def hash_embed(text: str, dim: int = HASH_DIM) -> list[float]:
    """Deterministic bag-of-words vector. Not semantic — its job is to prove the
    Qdrant round-trip (upsert + filtered query) without pulling an embedding model
    into the test, and it is the honest default for an offline course.

    Its limit is worth stating plainly, because a hash vector looks like a real
    one right up until you rely on it: "refunds" and "reimbursements" hash to
    unrelated buckets, so this retrieves on vocabulary overlap and nothing else.
    Set `ASSISTANT_EMBED_MODEL` for semantic recall (see `ollama_embed`)."""
    vec = [0.0] * dim
    for token in text.lower().split():
        h = int(hashlib.sha1(token.encode()).hexdigest(), 16)
        vec[h % dim] += 1.0
    norm = sum(v * v for v in vec) ** 0.5
    return [v / norm for v in vec] if norm else vec


def ollama_embed(host: str, model: str, timeout: float = 30.0) -> Callable[[str], list[float]]:
    """A real embedding function, behind one env var.

    Returns a callable rather than taking the text directly so the client (and
    its connection pool) is built once, at composition time, rather than per
    document — and so `QdrantStore` can probe it for the vector size instead of
    being told a dimension that has to be kept in sync by hand."""
    from ollama import Client  # lazy: the fast tier never imports it

    client = Client(host=host, timeout=timeout)

    def embed(text: str) -> list[float]:
        return list(client.embeddings(model=model, prompt=text)["embedding"])

    return embed


class QdrantStore:
    """RagStore's interface, backed by a real Qdrant collection.

    Points are keyed by `Chunk.id`, and the payload carries the provenance a
    citation needs: source, version, ordinal and character offsets. An
    auto-incrementing id would make every re-ingest a duplicate; a random one
    would make deletion impossible without a scan."""

    def __init__(
        self,
        url: str,
        collection: str = "assistant",
        embed: Callable[[str], list[float]] = hash_embed,
        dim: int | None = None,
    ) -> None:
        from qdrant_client import QdrantClient  # lazy: only when the real tier is on
        from qdrant_client.models import Distance, VectorParams

        self.client = QdrantClient(url=url)
        self.collection = collection
        self.embed = embed
        # Measured, not declared: the dimension belongs to whichever embedder was
        # injected, and a mismatch between it and the collection is a 400 from
        # Qdrant on the first write — after the deploy.
        self.dim = dim or len(embed("dimension probe"))
        if not self.client.collection_exists(collection):
            self.client.create_collection(
                collection,
                vectors_config=VectorParams(size=self.dim, distance=Distance.COSINE),
            )

    def _payload(self, chunk: Chunk, tenant: str) -> dict:
        return {
            "text": chunk.text, "tenant": tenant, "source": chunk.source,
            "version": chunk.version, "ordinal": chunk.ordinal,
            "start": chunk.start, "end": chunk.end,
        }

    def add(self, docs: list, tenant: str = DEFAULT_TENANT) -> int:
        from qdrant_client.models import PointStruct

        chunks = as_chunks(docs, tenant)
        if not chunks:
            return 0
        # A shorter revision of a source leaves orphan tail chunks behind —
        # ordinals 4 and 5 of yesterday's page, still indexed, still retrievable,
        # still citing a version that no longer exists. Clear them first.
        for source in {c.source for c in chunks}:
            keep = {c.ordinal for c in chunks if c.source == source}
            self._delete_where(tenant, source, exclude=keep)
        self.client.upsert(
            self.collection,
            points=[
                PointStruct(id=c.id, vector=self.embed(c.text),
                            payload=self._payload(c, tenant))
                for c in chunks
            ],
        )
        return len(chunks)

    def _filter(self, tenant: str, source: str | None = None):
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        must = [FieldCondition(key="tenant", match=MatchValue(value=tenant))]
        if source is not None:
            must.append(FieldCondition(key="source", match=MatchValue(value=source)))
        return Filter(must=must)

    def _delete_where(self, tenant: str, source: str, exclude: set[int]) -> None:
        stale = [
            point.id
            for point in self.client.scroll(
                self.collection, scroll_filter=self._filter(tenant, source), limit=1000
            )[0]
            if (point.payload or {}).get("ordinal") not in exclude
        ]
        if stale:
            self.client.delete(self.collection, points_selector=stale)

    def delete(self, source: str, tenant: str = DEFAULT_TENANT) -> int:
        found = self.client.scroll(
            self.collection, scroll_filter=self._filter(tenant, source), limit=1000
        )[0]
        if found:
            self.client.delete(self.collection, points_selector=[p.id for p in found])
        return len(found)

    def get(self, chunk_id: str, tenant: str = DEFAULT_TENANT) -> Chunk | None:
        points = self.client.retrieve(self.collection, ids=[chunk_id])
        for point in points:
            payload = point.payload or {}
            if payload.get("tenant") == tenant:
                return self._chunk(payload)
        return None

    def _chunk(self, payload: dict) -> Chunk:
        return Chunk(
            text=payload["text"], source=payload.get("source", "inline"),
            version=payload.get("version", ""), ordinal=payload.get("ordinal", 0),
            start=payload.get("start", 0), end=payload.get("end", 0),
            tenant=payload.get("tenant", DEFAULT_TENANT),
        )

    def search(self, query: str, k: int = 3, tenant: str = DEFAULT_TENANT) -> list[Chunk]:
        # the tenant filter runs SERVER-SIDE: a cross-user document is excluded
        # by Qdrant itself, not by post-hoc trimming in the application
        hits = self.client.query_points(
            self.collection,
            query=self.embed(query),
            limit=k,
            query_filter=self._filter(tenant),
        ).points
        return [self._chunk(h.payload) for h in hits if h.payload]


# --- generation: the Ollama tier -----------------------------------------------


#: A hard ceiling on generated tokens. The answers this assistant composes are one
#: to three sentences read off retrieved context, so this is roughly an order of
#: magnitude of headroom — it exists to bound the worst case, not to shape output.
#: Without it, "how long does a request take" has no answer: an unbounded
#: generation is a request whose duration is decided by the model's mood.
COMPLETION_TOKEN_CAP = 512


#: What every completion on the request path asks for, and the reason this module
#: has a constant instead of two bare call sites.
#:
#: `think=False` is the one that matters, and it is worth understanding rather
#: than copying. Reasoning models emit their deliberation as tokens you wait for
#: and then throw away, and "restate what this retrieved context says" is the kind
#: of task they deliberate hardest about, because there is nothing to work out.
#: Measured on a CPU-only container: 667 reasoning tokens at 0.52 tokens/second,
#: for a one-sentence answer that never arrived because the 60-second budget ran
#: out first. The same prompt with thinking off: 10 tokens.
#:
#: The cap alone would not have fixed it. Cap at 512 with thinking on and the
#: model spends all 512 thinking and returns an empty answer — bounded, useless,
#: and much harder to diagnose than a timeout.
#:
#: Ollama rejects `think` for a model that has no reasoning mode. That surfaces as
#: a failed completion, the fallback composer answers, and `/health` reports the
#: degradation — which is the right outcome for "you configured a model this code
#: has never been run against", and better than silently dropping the flag that
#: keeps the request path bounded.
BOUNDED = {"think": False, "options": {"num_predict": COMPLETION_TOKEN_CAP}}


def ollama_generate(
    prompt: str, *, host: str, model: str, timeout: float | None = None
) -> str:
    """One non-streaming completion against a local Ollama model.

    `timeout` is optional because the composer is allowed to take as long as a
    good answer takes, while the guard model in `guard.py` sits on the request
    path in front of it and is not."""
    from ollama import Client  # lazy

    response = Client(host=host, timeout=timeout).generate(
        model=model, prompt=prompt, **BOUNDED
    )
    return response["response"].strip()


def ollama_stream(prompt: str, *, host: str, model: str) -> Iterator[str]:
    """The same completion, yielded token-by-token as Ollama produces it — what
    the /ask/stream endpoint forwards as server-sent events.

    Bounded the same way, for a sharper reason: a client watching an SSE stream
    would sit through hundreds of tokens of deliberation before the first word of
    the answer, and a stream whose first chunk is minutes away is not a stream."""
    from ollama import Client  # lazy

    for part in Client(host=host).generate(model=model, prompt=prompt, stream=True, **BOUNDED):
        chunk = part["response"]
        if chunk:
            yield chunk


# --- tools: discover + invoke on a real MCP server ------------------------------


def _schema_of(spec: Any) -> dict:
    """A discovered tool's input schema. The v2 SDK models it as `input_schema`;
    the wire format and older clients spell it `inputSchema`. Accepting both
    costs one line and stops the planner losing its arguments to a rename."""
    return getattr(spec, "input_schema", None) or getattr(spec, "inputSchema", None) or {}


#: Discovery is a read, and a server that is still starting is the common reason
#: it fails, so this one retries.
MCP_DISCOVERY_POLICY = resilience.Policy(attempts=3, timeout=10.0)

#: Invocation does NOT retry, and the reason is that we cannot know whether it is
#: safe to. A discovered tool arrives as a name, a description and a JSON schema;
#: nothing in the MCP protocol says whether calling it twice charges a card twice.
#: Retrying an unknown remote effect on the strength of an optimistic guess is a
#: worse failure than surfacing the timeout, so the timeout is what it gets.
MCP_INVOKE_POLICY = resilience.ONCE


def mcp_tools(
    target: Any,
    discovery_policy: resilience.Policy = MCP_DISCOVERY_POLICY,
    invoke_policy: resilience.Policy = MCP_INVOKE_POLICY,
) -> tuple[list[dict], Callable[[str, dict], Any]]:
    """List a real MCP server's tools and return (specs, invoker) shaped exactly for
    `mcp_client.extend_assistant`. `target` is anything the v2 SDK's Client accepts:
    a URL string (streamable HTTP) in production, or an MCPServer instance in-memory.

    This is the real replacement for the injected-dict fake in mcp_client.py: the
    specs come from the server at runtime, so adding a tool server-side and
    restarting is all it takes for the assistant to gain it.

    Both paths are wrapped in a timeout, which is the part that matters most: an
    MCP server is a process someone else deployed, and a tool call to one is the
    easiest way for a request to hang forever on a dependency that this service
    does not own. The timeout is also budget-aware (`deadline.capped`), so a call
    made with four seconds of request left gets four seconds and not ten.
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
            # the input schema is the server's contract; `required` is the part
            # the planner needs to know whether it can call the tool at all
            return [
                {
                    "name": t.name,
                    "description": t.description or "",
                    "required_args": tuple(_schema_of(t).get("required", ())),
                }
                for t in listed.tools
            ]

    def call_tool(name: str, args: dict) -> Any:
        async def _call() -> Any:
            async with Client(target) as client:
                result = await client.call_tool(name, args)
                return [getattr(c, "text", str(c)) for c in result.content]

        return run_sync(_call)

    invoker = resilience.resilient(call_tool, invoke_policy)
    discover = resilience.resilient(lambda: run_sync(_list), discovery_policy)
    return discover(), invoker
