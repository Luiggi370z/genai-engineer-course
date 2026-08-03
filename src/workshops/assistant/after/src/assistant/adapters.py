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
import re
from collections.abc import Callable, Iterator
from dataclasses import replace
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


#: Named vectors, because the collection carries two arms per point rather than
#: one. Renaming either is a collection migration, which is why they are here and
#: not inline.
DENSE = "dense"
SPARSE = "keywords"


def sparse_terms(text: str):
    """Term frequencies as a Qdrant sparse vector — the keyword arm of hybrid.

    Deliberately NOT a BM25 implementation. The collection declares
    `Modifier.IDF`, so Qdrant holds the corpus statistics and does the weighting
    server-side; the client's whole job is to say which terms appeared and how
    often. That split is the point: IDF computed here would be IDF over whatever
    this process happens to have seen, which is not the corpus.

    Tokens are hashed into the index space rather than kept in a vocabulary,
    which is what lets a term appear for the first time without a reindex.
    """
    from qdrant_client.models import SparseVector

    counts: dict[int, float] = {}
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        index = int(hashlib.sha1(token.encode()).hexdigest()[:8], 16)
        counts[index] = counts.get(index, 0.0) + 1.0
    return SparseVector(indices=list(counts), values=list(counts.values()))


def distinctive_terms(text: str) -> set[str]:
    """Query tokens whose presence is evidence in itself: identifiers.

    The sparse arm earns its place by finding strings an embedder cannot place —
    `ZX-99417`, `E_TIMEOUT`, `CVE-2026-1`. When admission needs to know whether a
    sparse hit is real, "the query and the document share this exact token" is the
    honest test, and it costs no calibration.

    But only for tokens that MEAN something by being exact. Admitting on any shared
    word would undo abstention: ask an office-policy corpus how photosynthesis
    works and "work" appears verbatim in half of it. So a term qualifies when it
    carries a digit or is written in caps, and ordinary prose qualifies never.

    Tokenised the way `sparse_terms` tokenises, on `[a-z0-9]+`, so a term that
    qualifies here is a term that arm actually indexed: `ZX-99417` contributes
    `zx` and `99417`, and it is `99417` that does the work.
    """
    terms = set()
    for raw in re.findall(r"[A-Za-z0-9]+", text):
        if any(ch.isdigit() for ch in raw) or (raw.isupper() and len(raw) >= 3):
            terms.add(raw.lower())
    return terms


def collection_name(base: str, signature: str, dim: int) -> str:
    """`assistant__nomic-embed-text__768` — the store's identity, not just a name.

    Vectors written by one embedder are meaningless to another, and Qdrant only
    rejects the mismatch when the DIMENSION differs. Swap `nomic-embed-text` for
    another 768-dimensional model and every write succeeds, every search returns
    something, and the results are noise — the worst kind of failure, because it
    has no error in it. Putting the embedder and the width in the name makes a
    model change a new collection instead of a silent corruption of the old one.
    """
    tag = re.sub(r"[^a-zA-Z0-9_-]+", "-", signature).strip("-") or "unknown"
    return f"{base}__{tag}__{dim}"


class QdrantStore:
    """RagStore's interface, backed by a real Qdrant collection.

    Points are keyed by `Chunk.id`, and the payload carries the provenance a
    citation needs: source, version, ordinal and character offsets. An
    auto-incrementing id would make every re-ingest a duplicate; a random one
    would make deletion impossible without a scan.

    Retrieval is HYBRID, the way phase 2 teaches it: a dense arm for meaning, a
    sparse arm for the exact words, fused server-side with Reciprocal Rank
    Fusion. The deployed capstone ran dense-only for a while and the gap showed
    up as a specific class of miss — an error code, an order number, a policy
    name that the embedder had never seen and therefore placed nowhere useful.
    Dense retrieval is bad at strings that carry no meaning, which is most of
    what people paste into a support box.
    """

    def __init__(
        self,
        url: str,
        collection: str = "assistant",
        embed: Callable[[str], list[float]] = hash_embed,
        dim: int | None = None,
        signature: str = "hash",
        min_score: float = 0.0,
        rerank: Callable[[str, list[Chunk]], list[Chunk]] | None = None,
    ) -> None:
        from qdrant_client import QdrantClient  # lazy: only when the real tier is on
        from qdrant_client.models import (
            Distance,
            Modifier,
            SparseVectorParams,
            VectorParams,
        )

        self.client = QdrantClient(url=url)
        self.embed = embed
        self.min_score = min_score
        self.rerank = rerank
        # Measured, not declared: the dimension belongs to whichever embedder was
        # injected, and a mismatch between it and the collection is a 400 from
        # Qdrant on the first write — after the deploy.
        self.dim = dim or len(embed("dimension probe"))
        self.collection = collection_name(collection, signature, self.dim)
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(
                self.collection,
                vectors_config={
                    DENSE: VectorParams(size=self.dim, distance=Distance.COSINE)
                },
                # IDF lives on the server so the weighting is computed over the
                # whole collection rather than over one process's view of it.
                sparse_vectors_config={
                    SPARSE: SparseVectorParams(modifier=Modifier.IDF)
                },
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
                PointStruct(
                    id=c.id,
                    vector={DENSE: self.embed(c.text), SPARSE: sparse_terms(c.text)},
                    payload=self._payload(c, tenant),
                )
                for c in chunks
            ],
        )
        return len(chunks)

    def _filter(self, tenant: str, source: str | None = None):
        from qdrant_client.models import Condition, FieldCondition, Filter, MatchValue

        # Annotated as the union the client accepts rather than as the one class
        # built here: `list` is invariant, so a list[FieldCondition] is not a
        # list[Condition] to a type checker, and the error only appears on a
        # machine where the qdrant extra is installed.
        must: list[Condition] = [FieldCondition(key="tenant", match=MatchValue(value=tenant))]
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
            from qdrant_client.models import PointIdsList

            self.client.delete(self.collection, points_selector=PointIdsList(points=stale))

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
        """Dense + sparse, fused by Qdrant, thresholded, optionally reranked.

        The tenant filter runs SERVER-SIDE — on both arms, because a filter
        applied to one of two prefetches is not a filter. A cross-tenant
        document is excluded by Qdrant itself, never by trimming afterwards.
        """
        from qdrant_client.models import Fusion, FusionQuery, Prefetch

        tenant_filter = self._filter(tenant)
        # Over-fetch before fusing: RRF ranks by position, so a document that
        # only one arm found still needs to have been found. `k` candidates per
        # arm would make the fusion a formality.
        candidates = max(k * 4, 20)
        hits = self.client.query_points(
            self.collection,
            prefetch=[
                Prefetch(
                    query=self.embed(query), using=DENSE,
                    limit=candidates, filter=tenant_filter,
                ),
                Prefetch(
                    query=sparse_terms(query), using=SPARSE,
                    limit=candidates, filter=tenant_filter,
                ),
            ],
            query=FusionQuery(fusion=Fusion.RRF),
            limit=max(k, self._rerank_pool(k)),
            query_filter=tenant_filter,
        ).points
        # RRF scores are reciprocal ranks, not similarities: the top hit of a
        # search that found nothing relevant still scores like a top hit. So the
        # fused list cannot judge its own relevance, and admission goes back to the
        # arms, each of which is asked in units that mean something to it.
        #
        # Off by default (0.0) and set by the deployment, because the right cut is
        # a property of the corpus and the embedder rather than of this code. What
        # is NOT optional is that somebody decides: unset, this store cannot
        # abstain, and `service.build_store` reports that as a degradation rather
        # than leaving it to be discovered by an answer.
        kept = [
            replace(self._chunk(h.payload), score=h.score, scored_by="rrf")
            for h in hits
            if h.payload
        ]
        if self.min_score > 0.0:
            kept = self._admitted(query, kept, tenant)
        if self.rerank and kept:
            kept = self.rerank(query, kept)
        return kept[:k]

    def _rerank_pool(self, k: int) -> int:
        """How many candidates the reranker gets to choose from. Reranking the
        same `k` the caller asked for can only reorder them, which is not what a
        cross-encoder is for — it exists to promote something the retriever
        ranked eighth."""
        return k * 5 if self.rerank else k

    def _admitted(
        self, query: str, chunks: list[Chunk], tenant: str
    ) -> list[Chunk]:
        """Which candidates are relevant enough to ground an answer in — asked of
        each arm about its own hits, in its own units.

        Vector search never abstains: ask an unrelated question and it returns the
        three least-unrelated documents in the corpus, with no signal that it found
        nothing, and the composer grounds an answer in them. This is the gate that
        turns "the nearest thing I have" back into "I don't know", and it is the
        ONLY place in the request path where that judgement is made.

        It is also the gate that has now been got wrong twice in opposite
        directions, which is what makes the per-arm shape the point rather than an
        implementation detail:

          * a lexical filter downstream threw away the semantic hits the embedder
            existed to find;
          * replacing it with a single dense cosine floor threw away the exact
            matches the sparse arm existed to find — `ZX-99417` scored 0.535
            against a floor of 0.58 while being the only hit on an arm that had no
            doubt about it.

        Both failures are the same mistake: one arm's units used to judge the
        other's evidence. So the dense arm gets a cosine floor, which is the right
        question for semantic similarity, and the sparse arm gets an exact-term
        rule, which needs no calibration and cannot be expressed as a cosine.
        Either arm can admit; neither can veto.

        Each survivor carries the score of the arm that kept it and the name of
        that arm. Both travel into the citation, because a 1.96 that reads as a
        cosine is worse than no number at all.
        """
        cosine = self._dense_admits(query, tenant, len(chunks) * 2)
        exact = self._sparse_admits(query, tenant, chunks)
        kept = []
        for chunk in chunks:
            # Dense first when both arms admit, so the common case keeps reporting
            # a cosine and the citation contract downstream stays honest.
            if chunk.id in cosine:
                kept.append(replace(chunk, score=cosine[chunk.id], scored_by="cosine"))
            elif chunk.id in exact:
                kept.append(replace(chunk, score=exact[chunk.id], scored_by="sparse"))
        return kept

    def _dense_admits(self, query: str, tenant: str, limit: int) -> dict:
        """Dense hits at or above `min_score`, by id. The threshold is applied by
        Qdrant rather than here so a candidate below it is never transferred."""
        scored = self.client.query_points(
            self.collection,
            query=self.embed(query),
            using=DENSE,
            limit=limit,
            score_threshold=self.min_score,
            query_filter=self._filter(tenant),
        ).points
        return {point.id: point.score for point in scored}

    def _sparse_admits(self, query: str, tenant: str, chunks: list[Chunk]) -> dict:
        """Sparse hits that also contain a distinctive query term verbatim, by id.

        Two conditions, and the second is what keeps abstention working. The sparse
        arm ranks everything it can match, so "found by the sparse arm" alone is
        nearly as unselective as no gate at all — every document sharing the word
        "the" is on that list. Requiring an identifier to appear verbatim means the
        rule fires on the evidence the arm exists to produce and stays silent on
        prose, where the dense arm is the one with an opinion worth having.

        No threshold on the sparse score itself, deliberately: it is an IDF-weighted
        dot product whose scale depends on the corpus, so any constant here would be
        a number nobody could defend, calibrated against a corpus that will change.
        """
        terms = distinctive_terms(query)
        if not terms:
            return {}
        scored = self.client.query_points(
            self.collection,
            query=sparse_terms(query),
            using=SPARSE,
            limit=len(chunks) * 2,
            query_filter=self._filter(tenant),
        ).points
        admitted = {}
        for point in scored:
            text = (point.payload or {}).get("text", "")
            if terms & set(re.findall(r"[a-z0-9]+", text.lower())):
                admitted[point.id] = point.score
        return admitted


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
    _report_usage(response)
    return response["response"].strip()


def _report_usage(part: Any) -> None:
    """Hand the provider's own token counts to the meter.

    Ollama returns `prompt_eval_count` and `eval_count` on the final object of
    every completion, and this code used to throw them away and let a word count
    stand in — an approximation that reads exactly like a measurement once it is
    printed with a dollar sign next to it. Both or neither: a response missing
    one of them is not half-counted, it is uncounted, and `usage.measure` falls
    back to the estimate and labels it.
    """
    from assistant import usage

    tokens_in = _int_or_none(part, "prompt_eval_count")
    tokens_out = _int_or_none(part, "eval_count")
    if tokens_in is not None and tokens_out is not None:
        usage.report(tokens_in, tokens_out)


def _int_or_none(part: Any, key: str) -> int | None:
    value = part.get(key) if hasattr(part, "get") else getattr(part, key, None)
    return int(value) if isinstance(value, int) else None


def ollama_stream(prompt: str, *, host: str, model: str) -> Iterator[str]:
    """The same completion, yielded token-by-token as Ollama produces it — what
    the /ask/stream endpoint forwards as server-sent events.

    Bounded the same way, for a sharper reason: a client watching an SSE stream
    would sit through hundreds of tokens of deliberation before the first word of
    the answer, and a stream whose first chunk is minutes away is not a stream."""
    from ollama import Client  # lazy

    for part in Client(host=host).generate(model=model, prompt=prompt, stream=True, **BOUNDED):
        # The counts ride on the final object, after the last text chunk. Reading
        # every part rather than only the one flagged `done` costs nothing and
        # survives a provider that moves them.
        _report_usage(part)
        chunk = part["response"]
        if chunk:
            yield chunk


# --- tools: discover + invoke on a real MCP server ------------------------------


def _schema_of(spec: Any) -> dict:
    """A discovered tool's input schema. The v2 SDK models it as `input_schema`;
    the wire format and older clients spell it `inputSchema`. Accepting both
    costs one line and stops the planner losing its arguments to a rename."""
    return getattr(spec, "input_schema", None) or getattr(spec, "inputSchema", None) or {}


def _hints_of(spec: Any) -> dict:
    """The server's own claims about what a tool does: `readOnlyHint`,
    `destructiveHint`.

    Dropped on the floor until now, which left the client with no information at
    all — and `requires_approval` defaulting to False meant "no information"
    resolved to "safe". Carrying them through is not the same as believing them;
    `mcp_client` treats a hint as something that can only ever ADD caution. The
    word in the spec is "hint" and the spec means it: an annotation is an
    assertion by the same party that would benefit from lying.
    """
    annotations = getattr(spec, "annotations", None)
    if annotations is None:
        return {}

    def hint(camel: str) -> Any:
        if isinstance(annotations, dict):
            return annotations.get(camel)
        # the SDK models these snake_cased; the wire spells them camel
        snake = "".join("_" + c.lower() if c.isupper() else c for c in camel)
        return getattr(annotations, snake, getattr(annotations, camel, None))

    hints = {"read_only": hint("readOnlyHint"), "destructive": hint("destructiveHint")}
    return {k: v for k, v in hints.items() if v is not None}


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
                    # informs the gating decision in mcp_client; never makes it
                    **_hints_of(t),
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
