# 5.1 Four kinds of memory — reference

One store, four namespaces, and a `forget` that actually forgets.

```bash
make setup && make test        # 13 tests, offline, no model
uv run python -m src.memory    # the report: rows per kind, expired, missing source
make test-integration          # the one claim that needs real embeddings
```

## Why four kinds and not one bucket

| Kind | Holds | Lives for | The failure when you get it wrong |
|---|---|---|---|
| `working` | this run: task, recent turns, last result | one session | overflow — the earliest instruction falls out silently |
| `episodic` | specific past events | until no longer relevant | one incident hardens into a rule |
| `semantic` | durable facts about the user and world | until superseded | **staleness** — true when learned, never retired |
| `procedural` | how to do a job well | until the tool changes | it becomes a second, unreviewed system prompt |

Lump them together and you get an agent that forgets your timezone but vividly
recalls a tool error from March. The kinds are not taxonomy for its own sake: each
one has a different write policy and a different expiry story.

## Namespacing by payload, not by collection

`(user, kind)` lives in the payload and every read is a filtered search. Separate
collections per kind would work too, but payload namespacing is what gives you:

- **per-user isolation** — a semantic query cannot surface another user's fact
- **one filter delete** for "forget everything you know about me"
- **one collection to operate**, whatever the user count

## The TTL filter, and the trap in it

"Not expired" is *two* cases, and this is the whole reason `_filter` looks the way it
does:

```python
min_should=models.MinShould(conditions=[
    models.IsNullCondition(is_null=models.PayloadField(key="expires_at")),  # no expiry
    models.FieldCondition(key="expires_at", range=models.Range(gte=cutoff)),  # not yet
], min_count=1)
```

A plain `Range(gte=cutoff)` silently drops every row whose `expires_at` is `null` —
which is most of them. The symptom is an agent that remembers nothing, the cause is
one missing clause, and `test_rows_without_an_expiry_survive_the_ttl_filter` is the
test that pins it.

Expiry hides a row from `recall`, but `all()` and the report still see it. That is
deliberate: staleness should be auditable, not invisible.

## Forget means deleted

`test_forget_removes_the_row_rather_than_lowering_its_rank` asserts an **empty**
recall, not a lower score. A "deleted" fact that still ranks second is still going to
end up in a prompt on a quiet day — and the user who corrected it will see it again.

## What the fast tier can and cannot prove

The hash embedder is deterministic bag-of-words: it captures word overlap and nothing
else. That is enough for namespacing, expiry, deletion and provenance — the logic
this lesson is about. Paraphrase recall ("which timezone should I schedule in?"
finding "based in Lima") is a claim about *embeddings*, so it is marked `integration`
and runs against real vectors. Keep those two claims separate and your fast tier
stays honest and free.
