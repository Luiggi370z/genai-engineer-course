# ADR-0012 — Retrieval stores chunks with derived identity, not strings with counters

**Status:** accepted (amended — see "Amendment: the collection is named after the
embedder, and the search uses both arms")

## Context

The capstone's retrieval layer stored strings. `add(["..."])` appended to a list,
Qdrant got an auto-incrementing integer id, and `search()` handed back prose. It
passed its tests, and every one of the following was true at the same time:

**Re-ingesting the corpus duplicated it.** The id came from a counter, so the
same document loaded twice became two points, both retrievable, both citable.
The loader is the thing most likely to be re-run — after a crash, after a config
change, on a cron — so the failure mode was not exotic, it was scheduled.

**Nothing could be deleted.** There was no `delete` at all. A document withdrawn
by legal, a page discovered to be poisoned, a customer exercising erasure: all of
them required rebuilding the collection from scratch, which is why in practice
none of them would have happened.

**Citations were unfalsifiable.** `{"source": "rag"}` names the machine that did
the lookup, not the document. A reader cannot check it, an evaluator cannot score
it, and an answer that cites a hallucinated fact looks exactly like one that does
not.

**Long documents were one point each.** A 20-page policy embedded as a single
vector ranks against nothing in particular, and the paragraph that answers the
question is averaged into 19 pages of everything else.

**The embedding was a 64-dimension hash of the words.** Honest as an offline
default and clearly labelled as one, but there was no path to a real embedder:
the dimension was a hardcoded `64` in two places, so swapping the model meant a
400 from Qdrant on the first write after the deploy.

## Decision

**The unit of storage is a `Chunk`, not a string** — text plus source, version,
ordinal, character offsets and tenant. Everything below follows from having
somewhere to put that information.

**Identity is derived from position, not from content or arrival order.**
`uuid5(namespace, "tenant|source|ordinal")`. Deterministic, so a re-ingest is an
UPDATE. Excludes the text, so an *edit* replaces the paragraph instead of
shelving the old one next to the new one. Includes the tenant, so two customers'
copies of the same public document are two points. UUIDv5 rather than a hash
prefix because it is one of the two id types Qdrant accepts natively, which keeps
the in-memory tier and the real tier honest about each other.

**Versions are content hashes of the document body**, from the same
`provenance.digest` that stamps prompts and corpora (ADR-0011). An edit is
visible without anyone remembering to bump anything.

**Offsets are a checkable claim.** `body[start:end] == chunk.text`, asserted in
the tests, which is what makes a citation something a reader can verify against
the original rather than a snippet they have to take on faith. Character offsets,
not token offsets: tokens are the better unit and require a tokenizer, and these
have to be checkable in a text editor.

**Windows overlap.** 480 characters with 60 of overlap, so a sentence that
straddles a boundary is findable in both halves rather than in neither.

**`delete(source)` and `get(chunk_id)` are part of the interface**, not
extensions to it. Both are tenant-scoped by the same argument that scopes search.
`FallbackRag` deletes from *both* stores unconditionally, because a deletion that
only lands on the primary un-deletes itself the next time the standby answers.

**A short revision cleans up its own orphans.** Re-ingesting a document that got
shorter deletes the tail chunks whose ordinals no longer exist — otherwise
yesterday's paragraphs 4 and 5 stay indexed, stay retrievable, and keep citing a
version that is gone.

**The embedder is injected and its dimension is measured.**
`ASSISTANT_EMBED_MODEL` selects a real Ollama embedder; unset keeps `hash_embed`.
`QdrantStore` probes the injected function for the vector size rather than being
told, so a model swap cannot desynchronise from the collection config. The
fallback to hashing is *reported*, not silent — retrieval that quietly runs on
vocabulary overlap looks like retrieval right up until someone asks about
"reimbursements" and gets nothing about refunds.

**Screening preserves provenance.** `screen_chunks` redacts the text and keeps
the source, version and offsets, so a document with an email address in it is
still attributable and still deletable. The alternative creates an incentive to
screen less.

## Amendment: the collection is named after the embedder, and the search uses both arms

Three things were wrong with the decision above once it met a deployed stack.

**The injected embedder was never injected.** The compose file pulled
`nomic-embed-text` and never set `ASSISTANT_EMBED_MODEL`, so the store ran on the
64-dimension hash vector. Every check passed, because every check asked about
"refunds" using the word "refunds". A hash vector matches shared vocabulary, so a
question phrased in the corpus's own words works perfectly and a question phrased
in anyone else's returns nothing — which reads as a thin corpus, not as a
misconfiguration. `tier.embed` on `/health` now names the embedder in use and
says `hash (not semantic)` when that is the truth, and the E2E asks one question
that shares no vocabulary with its answer's source.

**"A new collection name plus a re-ingest" was advice, and advice does not
execute.** Qdrant validates the dimension of an incoming vector and nothing else,
so swapping one 768-wide model for another writes cleanly into the old
collection, searches cleanly, and returns noise. There is no error at any point.
The collection name therefore carries the embedder and its width —
`assistant__nomic-embed-text__768` — so a model swap creates a new, empty
collection: wrong on the first query, in a way somebody notices, instead of wrong
forever in a way nobody does.

**The capstone retrieved with one arm.** Phase 2 teaches dense + sparse fused
with RRF and the capstone shipped dense-only, which is the course contradicting
itself in the artifact it points at as the answer. `QdrantStore.search` now runs
both prefetches with a server-side `FusionQuery(Fusion.RRF)` — Qdrant's own
fusion rather than a Python reimplementation of it — with the tenant filter on
*both* arms, because a filter applied to one of two prefetches is not a filter.
Sparse vectors use the collection's IDF modifier, so term weighting is the
store's job rather than the client's.

**Vector search never abstains.** `ASSISTANT_MIN_SCORE` is a floor on the DENSE
similarity — not on the fused score, which is a reciprocal rank and means nothing
as a magnitude. Default 0.0, because the useful cut depends on the embedder and
the corpus and a wrong one abstains on good answers; the mechanism is what ships,
tuned per deployment. `ASSISTANT_RERANK_MODEL` adds an optional cross-encoder
over the fused candidates, which scores query and passage *together* rather than
comparing two vectors computed apart. It is off by default: a second model on the
request path, and hybrid already buys most of what it would. A missing
`fastembed` reports a degradation and retrieval carries on unreranked.

## Alternatives considered

Hashing the text into the id (turns every edit into a new point and orphans the
old one — the exact bug this replaces, wearing a nicer hat). Keeping the counter
and de-duplicating at query time (pays the cost on every read, forever, to avoid
paying it once on write). A `documents` table beside the vectors as the source of
truth for provenance (correct at scale, and a second store to keep consistent
with the first; the payload is enough at workshop sizes and the interface does
not change if it later is not). Token-based chunking with a real tokenizer
(better boundaries, an extra dependency in the fast tier, and offsets nobody can
check by hand). Returning `(text, metadata)` tuples instead of a dataclass (works
until the third field). Making the real embedder the default (the course must run
offline; a default that requires a model server is a default that fails on a
plane).

## Consequences

`search()` returns `Chunk` objects, which is a breaking change for every caller
that treated the result as strings. `rag.texts()` exists for the callers that
genuinely only want words — the composer and the planner — and `RagStore.search`
still returns strings so the Workshop-2 lesson is unaffected.

`ingested` now counts chunks, not documents. One long page reports as several,
which is the number that actually matters downstream: it is how many things can
come back from a search.

Chunking at 480 characters means a small corpus produces more points than before,
and the in-memory BM25 index is rebuilt on every `add`. Both are fine at workshop
sizes and both are the first things to change under real volume.

Switching `ASSISTANT_EMBED_MODEL` invalidates an existing collection — different
vectors, possibly a different dimension. Under the amendment this is handled by
the store rather than by remembering: the new model gets a new collection and the
old vectors stay where they are, unread. The cost is that a model swap needs a
re-ingest before the assistant can answer anything, which is the loud version of
a failure that used to be silent, and cheap because ids are stable.

Hybrid retrieval issues two prefetches per search instead of one query, and
over-fetches four times `k` per arm so RRF has something to fuse. At workshop
corpus sizes this is not measurable; it is the first thing to tune under volume.
The threshold check costs a third query when `ASSISTANT_MIN_SCORE` is set, which
is why the default leaves it off.
