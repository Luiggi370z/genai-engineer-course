"""The assistant itself — one pipeline, two delivery modes.

`Assistant` owns the request pipeline: screen the input, remember it, retrieve
and re-screen context, run the tool loop under a trace, then compose. `ask()`
returns the answer in one piece; `ask_stream()` yields it as SSE frames. Both
build on the same `_gather` so policy can never diverge between the two paths.

Everything here is deterministic and offline — the adapters that make it real
are chosen in service.py, and the HTTP surface lives in api.py.
"""
from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from assistant import auth, guardrails
from assistant.agent import Step, run
from assistant.audit_log import AuditLog
from assistant.composers import (
    Composer,
    StreamComposer,
    citations_for,
    offline_compose,
    word_stream,
)
from assistant.idempotency import IdempotencyStore
from assistant.observe import traced_registry, traced_run
from assistant.screening import harden_registry, screen_contexts
from assistant.settings import Settings
from assistant.tools import Tool


def rule_brain(contexts: list[str], registry: dict[str, Tool], compose: Composer):
    """A deterministic planner: fetch content when the goal implies it, gate a send,
    otherwise hand the evidence to the composer for the final answer."""

    def decide(goal: str, state: list[tuple[Step, Any]]) -> Step:
        low = goal.lower()
        ran = {step.tool for step, _ in state}
        wants_read = "email" in low or "inbox" in low
        if wants_read and "read_emails" in registry and "read_emails" not in ran:
            return Step("read_emails", {"limit": 5})
        sends = ("message the team", "send a message", "notify the team")
        wants_send = any(w in low for w in sends)
        if wants_send and "send_telegram" in registry and "send_telegram" not in ran:
            return Step("send_telegram", {"chat_id": "team", "message": goal})
        return Step("", {}, is_final=True, answer=compose(goal, contexts, state))

    return decide


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
    # an approval GRANTS ONE RUN — a count, not a standing permission. The
    # idempotency store makes a retried /approve a no-op instead of a second grant.
    grants: dict[str, int] = field(default_factory=dict)
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
        }

    def _gather(self, question: str, subject: str = auth.ANONYMOUS) -> dict:
        """Everything before composition, shared by ask() and ask_stream(): screen
        the input, remember it (namespaced by the caller's verified identity),
        retrieve context from the caller's tenant only, screen what came back, and
        run the tool loop with a capturing composer so the evidence comes back
        instead of a finished answer."""
        ok, cleaned = guardrails.screen(question)
        if not ok:
            self.audit_log.record("policy.blocked", subject, cleaned)
            return {"blocked": cleaned}
        self.memory.remember(cleaned, source=f"user:{subject}")
        contexts = screen_contexts(self.rag.search(cleaned, k=3, tenant=subject))
        captured: dict = {}

        def capture(goal: str, ctxs: list[str], state: list[tuple[Step, Any]]) -> str:
            captured["state"] = list(state)
            return ""

        registry = traced_registry(harden_registry(self.base_registry), self.rec.tracer)
        result = traced_run(
            run, cleaned, self.rec.tracer,
            decide=rule_brain(contexts, registry, capture),
            approvals={name: count > 0 for name, count in self.grants.items()},
            registry=registry,
        )
        self._consume_grants(result.audit)
        for entry in result.audit:
            if entry.startswith("ran: "):
                self.audit_log.record("tool.ran", subject, entry.removeprefix("ran: "))
        if result.pending is not None:
            self.audit_log.record("tool.pending", subject, result.pending.tool)
            return {"pending": result.pending, "contexts": contexts, "audit": result.audit}
        return {
            "goal": cleaned, "contexts": contexts,
            "state": captured.get("state", []), "audit": result.audit,
        }

    def _consume_grants(self, audit: list[str]) -> None:
        """Each run of a gated tool spends one grant — approval is per-execution,
        so an old approval cannot authorize next week's send."""
        for entry in audit:
            name = entry.removeprefix("ran: ")
            if name == entry:
                continue
            tool = self.base_registry.get(name)
            if tool and tool.requires_approval and self.grants.get(name, 0) > 0:
                self.grants[name] -= 1

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
                "pending": {"tool": pending.tool, "args": pending.args},
                "contexts": contexts, "citations": citations, "audit": gathered["audit"],
            }
        answer = self.compose(gathered["goal"], contexts, gathered["state"])
        if not guardrails.output_ok(answer):
            answer = "[redacted: output failed the safety gate]"
        return {"answer": answer, "contexts": contexts, "citations": citations,
                "audit": gathered["audit"]}

    def ask_stream(self, question: str, subject: str = auth.ANONYMOUS) -> Iterator[str]:
        """The same pipeline as ask(), as SSE frames: `chunk` events while the
        composer produces text, one `done` event with citations and the audit
        trail. The output gate runs on the accumulated text — if it fails, the
        `done` event carries the redaction and the client must discard the chunks
        it already rendered (the honest cost of streaming ahead of the gate)."""
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
                "pending": {"tool": pending.tool, "args": pending.args},
                "citations": citations, "audit": gathered["audit"],
            })
            return
        stream = self.stream_compose or word_stream(self.compose)
        parts: list[str] = []
        for chunk in stream(gathered["goal"], gathered["contexts"], gathered["state"]):
            parts.append(chunk)
            yield sse("chunk", {"text": chunk})
        answer = "".join(parts)
        if not guardrails.output_ok(answer):
            yield sse("done", {
                "answer": "[redacted: output failed the safety gate]", "redacted": True,
                "citations": citations, "audit": gathered["audit"],
            })
            return
        yield sse("done", {"answer": answer, "citations": citations,
                           "audit": gathered["audit"]})
