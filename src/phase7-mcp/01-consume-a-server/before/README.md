# 5.1 Consume a server (do this first)

Be a client before you build one — then any breakage is *your* client, not the server.
Fill the TODOs in `src/consume.py`. `src/demo_server.py` gives you something real to
point at, and v2's in-memory `Client` means the tests make genuine protocol calls
with no transport and no network.

```bash
make setup && make test
```

> **SDK version:** targets **`mcp>=2.0.0`** (spec 2026-07-28). See
> [`../SDK-V2-MIGRATION.md`](../SDK-V2-MIGRATION.md).
