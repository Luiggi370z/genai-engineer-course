"""Composition root — the capstone. Wire every layer you built across the workshops
into one running FastAPI service:

    request -> guardrails.screen (input)
            -> agent.run loop  (observe span)
                 -> tools (read-only content re-screened; irreversible ones gated)
                 -> RAG (offline BM25 or Qdrant)
                 -> memory (in-process or SQLite)
            -> guardrails.output_ok (response)

`build_assistant` and `create_app` are given — they select adapters from settings and
expose the HTTP surface. Your job is the composition LOGIC in between:
`harden_registry`, `rule_brain`, `_compose`, and `Assistant.ask`. Keep it offline and
deterministic so the fast tier (tests/test_service.py) stays green with no network.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from assistant.adapters import InMemoryRag
from assistant.memory import AssistantMemory
from assistant.observe import recorder
from assistant.settings import Settings
from assistant.tools import REGISTRY, Tool

ABSTAIN = "I don't know — that isn't in what I can see."


def harden_registry(registry: dict[str, Tool]) -> dict[str, Tool]:
    """TODO 1: re-screen the OUTPUT of every read-only tool with guardrails.screen()
    — a fetched email/page is exactly where an indirect injection arrives. Leave the
    irreversible (requires_approval) tools alone; the agent's approval gate covers
    those. Return a NEW registry; do not mutate the originals."""
    raise NotImplementedError


# Tool planning stays DETERMINISTIC in every tier — which tools may fire, and when
# a send is gated, is policy, and policy should not depend on model mood. What the
# model tier changes is answer COMPOSITION.
Composer = Callable[[str, list[str], list[Any]], str]


def rule_brain(contexts: list[str], registry: dict[str, Tool], compose: Composer):
    """TODO 2: return a deterministic `decide(goal, state) -> Step`. Fetch content
    with a read-only tool when the goal implies it, gate a "message the team" send,
    otherwise return a final Step whose answer comes from `compose(goal, contexts,
    state)`."""
    raise NotImplementedError


def offline_compose(goal: str, contexts: list[str], state: list[Any]) -> str:
    """TODO 3: the fast-tier composer — build the final answer from retrieved
    context plus any tool outputs in `state`; return ABSTAIN when there is nothing
    to ground an answer in."""
    raise NotImplementedError


def model_composer(host: str, model: str) -> Composer:
    """Real-tier composer (given): grounded generation against local Ollama.
    Abstention on empty evidence stays deterministic — a model given nothing to
    ground on should not be asked to improvise a refusal."""

    def compose(goal: str, contexts: list[str], state: list[Any]) -> str:
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
        """TODO 4: the pipeline. screen() the input (refuse if blocked); remember the
        turn; retrieve contexts; run agent.run under observe.traced_run with a
        harden+trace-wrapped registry, `rule_brain(contexts, registry, self.compose)`
        and self.approvals; return a pending payload if the loop paused; otherwise
        output_ok() the answer and return it with contexts and audit."""
        raise NotImplementedError


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
        return {"status": "ok", "tier": assistant.tier()}

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
