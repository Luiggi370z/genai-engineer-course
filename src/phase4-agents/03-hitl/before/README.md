# 4.3 Human-in-the-loop

**Goal.** Build a durable approval gate: irreversible actions (send/pay/delete/schedule)
pause instead of running, the pause is persisted to disk, and a human's decision
resumes it by token — even after the process dies. Durability is what separates
HITL from an `if` statement.
**Prerequisite.** 4.2 Tools (you know why irreversible actions need a human gate).
**Effort.** ~40 min · gentle

## Do this

```bash
make setup && make test     # 5 failing tests — read them, they are the spec
$EDITOR src/hitl.py         # fill TODO 1 (Runner.act) and TODO 2 (Runner.resume)
make check                  # green: ruff + pyright + pytest, all offline
```

## What the first failure means

`test_reversible_action_runs_immediately` fails because `Runner.act` isn't built
yet: a reversible action like `read` should just run. But the test that defines the
lesson is `test_pending_survives_a_restart` — a brand-new `Runner` over the same
store file must be able to resume a pause it never saw created. That only works if
`act` persists the `PendingApproval` to disk, not just to memory.

## Done when

- [ ] `make check` is green (lint, types, fast tests).
- [ ] A pending approval survives a simulated crash: a fresh `Runner` on the same
      store resumes it by token (the restart test pins this).
- [ ] `resume(token, approved=False)` rejects without ever executing the action.

## Stuck?

1. `act` branches on `action in IRREVERSIBLE`: run now, or mint a token, build a
   `PendingApproval`, save it, and return it — without calling the tool.
2. Persist `self._pending` as JSON at `self.store` on every change, and load it in
   (or before) `resume` so a new instance sees old pauses. `resume` pops the entry,
   then either runs `self.tools[action](**args)` or returns a rejected status.

## Going further (optional integration lane)
`make test-integration` proves the same mechanics in real LangGraph: `interrupt()`
suspends the graph, a SQLite checkpointer persists it, and `Command(resume=...)`
continues it by `thread_id` — including a restart test where a brand-new graph
instance over the same checkpoint file completes the pause. Needs only the opt-in
install (LangGraph + the SQLite checkpointer, a heavy dependency tree) — the nodes
are deterministic, so no model, GPU, or network. Skippable: the fast tier already
proves the logic.
