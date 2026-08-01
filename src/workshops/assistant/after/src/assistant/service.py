"""Composition root — the capstone. A FastAPI service that wires every layer built
across the workshops into one running thing:

    request -> guardrails.screen (input)
            -> agent.run loop  (observe span)
                 -> tools (read-only content re-screened; irreversible ones gated)
                 -> RAG (offline BM25 or Qdrant)
                 -> memory (in-process or SQLite)
            -> guardrails.output_ok (response)

Everything is offline and deterministic by default, so the fast tier drives the real
FastAPI app with a TestClient and no network. Setting the env vars in settings.py
swaps in the real adapters without touching this file's logic — that is the whole
point of composing against interfaces.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from assistant import guardrails
from assistant.adapters import InMemoryRag
from assistant.agent import Step, run
from assistant.memory import AssistantMemory
from assistant.observe import recorder, traced_registry, traced_run
from assistant.settings import Settings
from assistant.tools import REGISTRY, Tool

ABSTAIN = "I don't know — that isn't in what I can see."


# --- tool hardening: fetched content is untrusted -------------------------------


def harden_registry(registry: dict[str, Tool]) -> dict[str, Tool]:
    """Re-screen the OUTPUT of every read-only tool. A fetched email or web page is
    exactly where an indirect injection arrives, so its content is run back through
    the same L1 screen as user input; an irreversible tool is left to the agent's
    approval gate. Returns a new registry — the originals are untouched."""

    def wrap(tool: Tool) -> Tool:
        if tool.requires_approval:
            return tool  # gated by HITL, not by content screening

        def guarded(*args: Any, **kwargs: Any) -> Any:
            ok, cleaned = guardrails.screen(str(tool.fn(*args, **kwargs)))
            return {"content": cleaned} if ok else {"blocked": cleaned}

        return Tool(tool.name, guarded, tool.requires_approval, tool.doc)

    return {name: wrap(tool) for name, tool in registry.items()}


# --- the planner: rule-based steps, swappable answer composition ----------------
#
# Tool planning stays DETERMINISTIC in every tier — which tools may fire, and when
# a send is gated, is policy, and policy should not depend on model mood. What the
# model tier changes is answer COMPOSITION: the offline composer stitches context
# together; the Ollama composer writes grounded prose from the same evidence.

Composer = Callable[[str, list[str], list[tuple[Step, Any]]], str]


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


def offline_compose(goal: str, contexts: list[str], state: list[tuple[Step, Any]]) -> str:
    """Fast-tier composer: deterministic, offline, honest about its limits."""
    fetched = [str(out) for _, out in state]
    if contexts:
        answer = contexts[0]
        if fetched:
            answer += " (" + "; ".join(fetched) + ")"
        return answer
    if fetched:
        return " ".join(fetched)
    return ABSTAIN


def model_composer(host: str, model: str) -> Composer:
    """Real-tier composer: grounded generation against local Ollama. Abstention on
    empty evidence stays DETERMINISTIC — a model given nothing to ground on should
    not be asked to improvise a refusal."""

    def compose(goal: str, contexts: list[str], state: list[tuple[Step, Any]]) -> str:
        evidence = list(contexts) + [str(out) for _, out in state]
        if not evidence:
            return ABSTAIN
        from assistant.adapters import ollama_generate

        lines = "\n".join(f"- {item}" for item in evidence)
        prompt = (
            "Answer the question using ONLY the evidence below, in one or two "
            f"sentences. If the evidence does not answer it, reply exactly: {ABSTAIN}\n\n"
            f"Evidence:\n{lines}\n\nQuestion: {goal}"
        )
        return ollama_generate(prompt, host=host, model=model)

    return compose


# --- the assembled assistant ----------------------------------------------------


@dataclass
class Assistant:
    settings: Settings
    rag: Any
    memory: Any
    base_registry: dict[str, Tool]
    rec: Any
    compose: Composer = offline_compose
    approvals: dict[str, bool] = field(default_factory=dict)

    def tier(self) -> dict[str, str]:
        s = self.settings
        return {
            "rag": "qdrant" if s.qdrant_url else "in-memory",
            "memory": "sqlite" if s.assistant_db else "in-process",
            "brain": "ollama" if s.ollama_host else "rule-based",
            "tools": "mcp+builtin" if s.mcp_server else "builtin",
            "otlp": "on" if s.otlp_endpoint else "in-memory-only",
        }

    def ask(self, question: str) -> dict:
        ok, cleaned = guardrails.screen(question)
        if not ok:
            return {"answer": "I can't help with that request.", "blocked": cleaned,
                    "contexts": [], "audit": []}
        self.memory.remember(cleaned, source="user")
        contexts = self.rag.search(cleaned, k=3)
        registry = traced_registry(harden_registry(self.base_registry), self.rec.tracer)
        result = traced_run(
            run, cleaned, self.rec.tracer,
            decide=rule_brain(contexts, registry, self.compose),
            approvals=self.approvals, registry=registry,
        )
        if result.pending is not None:
            pending = result.pending
            return {
                "answer": f"'{pending.tool}' needs approval before it can run.",
                "pending": {"tool": pending.tool, "args": pending.args},
                "contexts": contexts, "audit": result.audit,
            }
        answer = result.text
        if not guardrails.output_ok(answer):
            answer = "[redacted: output failed the safety gate]"
        return {"answer": answer, "contexts": contexts, "audit": result.audit}


def build_assistant(settings: Settings | None = None) -> Assistant:
    settings = settings or Settings.from_env()

    if settings.qdrant_url:
        from assistant.adapters import QdrantStore
        rag: Any = QdrantStore(settings.qdrant_url, settings.qdrant_collection)
    else:
        rag = InMemoryRag()

    if settings.assistant_db:
        from assistant.sqlite_memory import SqliteMemory
        memory: Any = SqliteMemory(settings.assistant_db)
    else:
        memory = AssistantMemory()

    registry = dict(REGISTRY)
    if settings.mcp_server:
        from assistant.adapters import mcp_tools
        from assistant.mcp_client import extend_assistant
        discovered, invoker = mcp_tools(settings.mcp_server)
        registry = extend_assistant(registry, discovered, invoker)

    compose = (
        model_composer(settings.ollama_host, settings.ollama_model)
        if settings.ollama_host
        else offline_compose
    )

    return Assistant(
        settings=settings, rag=rag, memory=memory, base_registry=registry,
        rec=recorder(otlp_endpoint=settings.otlp_endpoint), compose=compose,
    )


# --- HTTP surface ---------------------------------------------------------------


class AskBody(BaseModel):
    question: str


class IngestBody(BaseModel):
    docs: list[str]


class ApproveBody(BaseModel):
    tool: str


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="GenAI assistant capstone")
    assistant = build_assistant(settings)
    app.state.assistant = assistant

    @app.get("/health")
    def health() -> dict:
        # spans_recorded lets an end-to-end verifier confirm observability is live
        # from outside the process — the in-memory exporter is always attached.
        return {
            "status": "ok",
            "tier": assistant.tier(),
            "spans_recorded": len(assistant.rec.spans()),
        }

    @app.post("/ingest")
    def ingest(body: IngestBody) -> dict:
        return {"ingested": assistant.rag.add(body.docs)}

    @app.post("/ask")
    def ask(body: AskBody) -> dict:
        return assistant.ask(body.question)

    @app.post("/approve")
    def approve(body: ApproveBody) -> dict:
        assistant.approvals[body.tool] = True
        return {"approved": body.tool}

    return app
