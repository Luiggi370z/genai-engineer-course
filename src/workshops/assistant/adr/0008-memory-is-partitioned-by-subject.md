# ADR-0008 — Memory is partitioned by subject, not labelled with one

**Status:** accepted

## Context

Both memory backends take a `user` and scope every read and write to it:
`SqliteMemory` filters on a `user` column, `AssistantMemory` keeps its own dict.
The composition root passed neither. It built one store with the default
`user="me"` and distinguished callers by writing `source=f"user:{subject}"` into
each row.

`recall` does not read `source`. It matched on text alone, across everyone. The
retrieval path had been fixed for exactly this — `rag.search` takes a `tenant`
and Qdrant filters server-side — and memory, the store that holds the *personal*
data, had not.

Nothing about the defect looks wrong from outside. Every caller gets sensible
answers, the database honestly records who said what, and the tests pass. It
fails only when two people's words overlap, which is to say in production and
not in the suite.

## Decision

One store per subject, built on first sight by a factory the composition root
supplies:

```python
TenantMemory(lambda subject: SqliteMemory(db, user=subject))
```

Isolation then comes from scoping the backends already implement, rather than
from a filter every call site has to remember to apply. Neither backend changed
to gain it. The partition lands where the backend keeps it — a column in the
shared SQLite file, a private dict in process — and the caller does not care
which.

`recall` requires a subject and never crosses one. `all()` deliberately does
cross, because it is the operator's view: "what has this service remembered" is
a question that needs the whole answer. The asymmetry is the only sharp edge and
it is documented at both ends.

## Alternatives considered

Add a `user=` argument to every `recall` call site (one forgotten call site is
the same leak, and there is no test that catches the one you forgot). Filter on
`source` after recall (post-hoc trimming — the same anti-pattern the Qdrant
tenant filter exists to avoid, and it ranks a stranger's memory into the top-k
before discarding it). One database file per subject (real isolation, and it
turns a backup into a directory walk and a schema migration into a fleet
operation). Encrypt per subject (defends a different threat — a stolen file, not
a crossed query).

## Consequences

A store is created per subject seen, so a service with many users holds many
small connections to one file; SQLite handles this, but it is a real resource
and a reason `TenantMemory` caches. Recall cannot be tested without deciding
whose recall it is, which is the point. Anonymous callers share one partition —
correct, since they share one identity — and that is an argument for turning the
JWT gate on, not against the partition.
