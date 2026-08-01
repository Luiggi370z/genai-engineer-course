# 5.1 Four kinds of memory

Give the agent a memory you can audit, expire and delete — on the retrieval stack you
already built in Phase 2.

```bash
make setup && make test        # 13 failures; read them, they are the spec
uv run python -m src.memory    # the report you're working toward
```

## Your job

Implement, in `src/memory.py`:

| Method | The interesting part |
|---|---|
| `write` | refuse a blank `source`; `ttl_days=None` must store `None`, not `0` |
| `recall` | filtered search — one namespace, expired rows already excluded |
| `all` | `scroll`, not search: listing is not ranking |
| `forget` | delete the point, do not lower its rank |
| `forget_all` | one filter delete = "forget everything you know about me" |
| `_scope` | `(user, kind)` as filter conditions |
| `_filter` | `_scope` plus the TTL rule |
| `classify` | route a claim to one of the four kinds |

## The two places people get this wrong

**Expiry.** "Not expired" is two cases: the row has no expiry at all, or its expiry is
in the future. A single range condition drops every `null` row, and your agent
forgets everything. The fix is a `min_should` clause with `min_count=1` — one of the
tests exists purely to catch this.

**Forgetting.** It is tempting to down-weight a corrected fact. Don't. The test
asserts an empty recall, because a row that still ranks second will resurface in a
prompt eventually, and the user who corrected you will notice.

## Then do it for your own assistant

Wire this store into the assistant from Workshop 4 and answer three questions in your
repo: what does it write (and what does it refuse to write), what expiry does each
kind get, and what happens when the user corrects a fact. Those three answers are the
memory design — the code is the easy part.
