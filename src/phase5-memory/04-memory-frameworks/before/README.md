# 5.4 Mem0 vs LangMem

Implement one memory protocol three times — a fake, Mem0, LangMem — and run one contract
suite over all three.

```bash
make setup && make test        # 10 failures against the fake; that's the spec
make test-integration          # the same contract against the real libraries
```

## Your job, in order

1. **`FakeStore`** in `src/store.py` — a dict and `overlap()`. Get the contract green
   offline first; it is the control for everything after.
2. **`Mem0Store`** in `src/adapters.py` — `Memory.from_config(MEM0_CONFIG)`, then `add`
   and `search`.
3. **`LangMemStore`** — the manage tool with a typed schema, reads from the LangGraph
   store.

The contract suite is given. Do not weaken it to make an adapter pass — that is the one
move that defeats the whole exercise.

## Run before you write

Both libraries moved recently. Open a REPL, make the call, print what comes back:

```python
from mem0 import Memory
m = Memory.from_config(MEM0_CONFIG)
print(m.add("Lu works in UTC-5", user_id="me:semantic", infer=False))
print(m.search("timezone", filters={"user_id": "me:semantic"}, top_k=5))
```

Three surprises are waiting for you, and finding them yourself is the lesson: what
`add()` does by default when you leave `infer` alone, which argument carries the
namespace in 2.x, and what shape LangMem stores a typed schema in.

## The judgement to write down

At the end, one paragraph in the repo: which one you would ship, what you verified it
against, and what would change your mind. Check the last release date of both before
you decide — one of them will tell you something.

Needs Ollama running with `nomic-embed-text` pulled for the Mem0 path. No API keys.
