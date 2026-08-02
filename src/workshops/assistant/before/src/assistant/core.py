"""The assistant itself — one pipeline, two delivery modes.

`Assistant` owns the request pipeline: screen the input, remember it, retrieve
and re-screen context, run the tool loop under a trace, then compose. `ask()`
returns the answer in one piece; `ask_stream()` yields it as SSE frames. Both
build on the same `_gather` so policy can never diverge between the two paths.

Your TODOs here are the planner (`rule_brain`, TODO 2) and the shared pipeline
(`Assistant._gather`, TODO 4); ask() and ask_stream() are given and build on
them. Keep everything offline and deterministic — the adapters that make it
real are chosen in service.py, and the HTTP surface lives in api.py.
"""
from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from assistant import auth, guardrails
from assistant.approvals import ApprovalStore, args_fingerprint
from assistant.audit_log import AuditLog
from assistant.composers import (
    Composer,
    StreamComposer,
    citations_for,
    offline_compose,
    word_stream,
)
from assistant.idempotency import IdempotencyStore
from assistant.output_gate import gated_chunks
from assistant.settings import Settings
from assistant.tools import Tool


def rule_brain(contexts: list[str], registry: dict[str, Tool], compose: Composer):
    """TODO 2: return a deterministic `decide(goal, state) -> Step`. Fetch content
    with a read-only tool when the goal implies it, gate a "message the team" send,
    otherwise return a final Step whose answer comes from `compose(goal, contexts,
    state)`."""
    raise NotImplementedError


def sse(event: str, data: dict) -> str:
    """One server-sent-events frame."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@dataclass
class Assistant:
    settings: Settings
    rag: Any
    memory: Any
    base_registry: dict[str, Tool]
    rec: Any
    compose: Composer = offline_compose
    stream_compose: StreamComposer | None = None
    # an approval GRANTS ONE RUN of ONE EXACT CALL by ONE SUBJECT — see
    # approvals.py for why a name -> bool flag is four separate holes. The
    # idempotency store makes a retried /approve a no-op instead of a second grant.
    approvals: ApprovalStore = field(default_factory=ApprovalStore)
    idempotency: IdempotencyStore = field(default_factory=IdempotencyStore)
    # component -> reason, filled in when a real adapter fails and the offline
    # default takes over; /health turns non-empty into status "degraded"
    degraded: dict[str, str] = field(default_factory=dict)
    # the persistent who-did-what trail: policy decisions, tool runs, approvals
    audit_log: AuditLog = field(default_factory=AuditLog)

    def tier(self) -> dict[str, str]:
        s = self.settings
        return {
            "rag": "qdrant" if s.qdrant_url else "in-memory",
            "memory": "sqlite" if s.assistant_db else "in-process",
            "brain": "ollama" if s.ollama_host else "rule-based",
            "tools": "mcp+builtin" if s.mcp_server else "builtin",
            "otlp": "on" if s.otlp_endpoint else "in-memory-only",
            "auth": "jwt" if s.jwt_secret else "off",
            "connectors": (
                "real" if (s.telegram_bot_token or s.news_feed_url) else "stubs"
            ),
            # surfaced so an operator can see from OUTSIDE the process whether the
            # outbound gate is screening before release or after it
            "stream": s.stream_mode,
        }

    def _gather(self, question: str, subject: str = auth.ANONYMOUS) -> dict:
        """TODO 4: everything before composition, shared by ask() and ask_stream().

        - screen() the input; if blocked, record ("policy.blocked", subject,
          reason) in self.audit_log and return {"blocked": reason}
        - remember the turn with source=f"user:{subject}" (memory namespace)
        - retrieve with self.rag.search(cleaned, k=3, tenant=subject) and pass
          the docs through screening.screen_contexts() — a poisoned document is
          dropped BEFORE it becomes evidence
        - run agent.run under observe.traced_run with a registry wrapped by
          screening.harden_registry (your TODO 1) then observe.traced_registry,
          a `capture` composer that RECORDS its state argument and returns ""
          (the callers compose afterwards), and `consume=` a callable that spends
          one of THIS subject's grants for the exact call:
              lambda name, args: self.approvals.consume(subject, name, args)
          Pass `consume`, not an `approvals` allow-list: the grant has to be taken
          against the arguments actually about to run.
        - audit-log every "ran: X" entry as ("tool.ran", subject, X), naming the
          grant it spent when result.approval_ids has one — the id is what ties
          the /approve response, the log row and the span together; a paused run
          is ("tool.pending", subject, tool)
        - return {"pending": result.pending, "contexts": ..., "audit": ...} if
          the loop paused, else {"goal": cleaned, "contexts": ..., "state":
          captured state, "audit": result.audit}
        """
        raise NotImplementedError

    def ask(self, question: str, subject: str = auth.ANONYMOUS) -> dict:
        gathered = self._gather(question, subject)
        if "blocked" in gathered:
            return {"answer": "I can't help with that request.", "blocked": gathered["blocked"],
                    "contexts": [], "citations": [], "audit": []}
        contexts = gathered["contexts"]
        citations = citations_for(contexts)
        if "pending" in gathered:
            pending = gathered["pending"]
            return {
                "answer": f"'{pending.tool}' needs approval before it can run.",
                # args and their fingerprint travel with the pause: approving is
                # approving THIS call, so the client has to echo it back
                "pending": {"tool": pending.tool, "args": pending.args,
                            "args_hash": args_fingerprint(pending.args)},
                "contexts": contexts, "citations": citations, "audit": gathered["audit"],
            }
        answer = self.compose(gathered["goal"], contexts, gathered["state"])
        if not guardrails.output_ok(answer):
            answer = "[redacted: output failed the safety gate]"
        return {"answer": answer, "contexts": contexts, "citations": citations,
                "audit": gathered["audit"]}

    def ask_stream(self, question: str, subject: str = auth.ANONYMOUS) -> Iterator[str]:
        """The same pipeline as ask(), as SSE frames: `chunk` events carrying text
        the output gate has already cleared, then one `done` event with citations
        and the audit trail.

        The gating lives in output_gate.py, which holds a window back so nothing
        reaches the client before it has been screened — a streamed answer and a
        batch answer are subject to the same gate, not to a gate and an apology.
        """
        gathered = self._gather(question, subject)
        if "blocked" in gathered:
            yield sse("done", {
                "answer": "I can't help with that request.",
                "blocked": gathered["blocked"], "citations": [], "audit": [],
            })
            return
        citations = citations_for(gathered["contexts"])
        if "pending" in gathered:
            pending = gathered["pending"]
            yield sse("done", {
                "answer": f"'{pending.tool}' needs approval before it can run.",
                "pending": {"tool": pending.tool, "args": pending.args,
                            "args_hash": args_fingerprint(pending.args)},
                "citations": citations, "audit": gathered["audit"],
            })
            return
        stream = self.stream_compose or word_stream(self.compose)
        produced = stream(gathered["goal"], gathered["contexts"], gathered["state"])
        for kind, text in gated_chunks(produced, self.settings.stream_mode):
            if kind == "chunk":
                yield sse("chunk", {"text": text})
            elif kind == "blocked":
                yield sse("done", {
                    "answer": text, "redacted": True,
                    "citations": citations, "audit": gathered["audit"],
                })
            else:
                yield sse("done", {"answer": text, "citations": citations,
                                   "audit": gathered["audit"]})
