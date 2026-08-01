# 5.4 Mem0 vs LangMem — reference

Own the interface, rent the implementation. One protocol, three implementations, one
contract suite.

```bash
make setup && make test        # 10 tests against the fake: no vendor, no network
make test-integration          # the SAME contract against Mem0 and LangMem
```

The integration run is the point of the lesson: 7 identical assertions × 2 rented
adapters, green against real libraries on a local model with no API key.

## What each rental actually is

| | Mem0 2.0.14 | LangMem 0.0.30 |
|---|---|---|
| Mental model | a memory **service**: add turns, it extracts and consolidates | typed memory schemas over the LangGraph store |
| Write path | `add(...)`, and by default it calls an LLM to rewrite and merge | a tool call that puts a typed object in the store |
| Expiry | native (`expiration_date`, `show_expired`) | none — your adapter enforces it |
| Namespacing | `user_id` string | store namespace tuple |
| Needs a model | yes (embedder; LLM too unless `infer=False`) | no, for write and search |
| Last release | days old at time of writing | **2025-10-27** |

## Three things you only learn by running it

**`infer=True` is the default.** Mem0's `add()` sends your text to an LLM to be
rewritten and merged with existing memories. That is genuinely its selling point — and
an unbudgeted call on the write path. The adapter passes `infer=False` so writes stay
deterministic; flipping it is a decision with a latency and cost tag, not a config
detail.

**2.x moved entity ids into `filters`.** `search(query, filters={"user_id": ...},
top_k=k)`. The `user_id=` kwarg you will find in tutorials is 1.x, and `top_k` is not
`limit`. This is what pinning versions and reading release notes is *for*.

**LangMem nests your schema.** A typed write comes back out as
`{"content": {"content": ..., "source": ..., "expires_at": ...}}`, which nobody
documents. `_unwrap` exists because the shape surprised us, and it lives in the adapter
so nothing else in the codebase ever learns about it.

## Why the contract suite is the deliverable

`tests/test_contract.py` defines seven behaviours — recall works, provenance survives,
a blank source is refused, kinds stay isolated, `forget` deletes, expired rows stay
gone, `k` is respected — and runs them against every adapter. The fake keeps the fast
tier hermetic; the rented adapters prove the abstraction is real rather than aspirational.

When one adapter fails a check and the others pass, you have found a difference that
would otherwise have shipped. LangMem's missing TTL is exactly that: the store has no
expiry concept, so the adapter filters expired rows itself, and the contract does not
bend to whatever features a vendor happens to ship this quarter.

## The adoption verdict

LangMem's release gap is not a reason to sneer — it is the reason the pattern matters.
LangMem is a thin layer over LangGraph's store, and the store is the durable part; if
the layer stops moving you keep the store and drop the layer. Mem0 does more on your
behalf and asks for a model to do it. Either is a defensible choice. Depending directly
on either one throughout your codebase is not.

Write your own verdict in the repo, with the version you verified and the date. That
sentence is worth more in an interview than knowing the API.
