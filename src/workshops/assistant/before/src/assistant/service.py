"""Composition root — the capstone. `build_assistant` wires every layer you built
across the workshops into one running thing:

    request -> auth (optional Bearer JWT, env-gated)      [api.py — given]
            -> guardrails.screen (input)                  [core.py]
            -> agent.run loop  (observe span)             [core.py]
                 -> tools (screening.py re-screens read-only content)
                 -> RAG (offline BM25 or Qdrant)          [adapters.py]
                 -> memory (in-process or SQLite)
            -> compose (offline stitcher or Ollama)       [composers.py]
                 -> degraded fallbacks on failure         [fallbacks.py — given]
            -> guardrails.output_ok (response)            [core.py]

This module and api.py are GIVEN — they select adapters from settings, wire the
degraded-operation fallbacks, and expose the HTTP surface including /ask/stream,
the JWT gate, load shedding, idempotent approvals, and the audit log. Your job
is the composition LOGIC in between: `harden_registry` (screening.py, TODO 1),
`rule_brain` (core.py, TODO 2), `offline_compose` (composers.py, TODO 3), and
the `Assistant._gather` pipeline (core.py, TODO 4) that ask() and ask_stream()
both build on. Keep it offline and deterministic so the fast tier
(tests/test_service.py) stays green with no network.
"""
from __future__ import annotations

from typing import Any

from assistant.adapters import InMemoryRag
from assistant.approvals import ApprovalStore
from assistant.audit_log import AuditLog
from assistant.composers import (
    Composer,
    StreamComposer,
    model_composer,
    model_stream_composer,
    offline_compose,
    word_stream,
)
from assistant.core import Assistant
from assistant.fallbacks import FallbackRag, fallback_composer, fallback_stream
from assistant.idempotency import IdempotencyStore
from assistant.memory import AssistantMemory
from assistant.observe import recorder
from assistant.settings import Settings
from assistant.tools import REGISTRY, Tool


def build_assistant(settings: Settings | None = None) -> Assistant:
    settings = settings or Settings.from_env()

    degraded: dict[str, str] = {}

    def report(component: str, reason: str) -> None:
        degraded[component] = reason

    if settings.qdrant_url:
        from assistant.adapters import QdrantStore
        rag: Any = FallbackRag(
            QdrantStore(settings.qdrant_url, settings.qdrant_collection),
            InMemoryRag(), report,
        )
    else:
        rag = InMemoryRag()

    if settings.assistant_db:
        from assistant.sqlite_memory import SqliteMemory
        memory: Any = SqliteMemory(settings.assistant_db)
    else:
        memory = AssistantMemory()

    registry = dict(REGISTRY)
    if settings.telegram_bot_token and "send_telegram" in registry:
        from assistant.connectors import telegram_sender
        stub = registry["send_telegram"]
        registry["send_telegram"] = Tool(
            stub.name, telegram_sender(settings.telegram_bot_token), True, stub.doc
        )
    if settings.news_feed_url and "read_news" in registry:
        from assistant.connectors import news_fetcher
        stub = registry["read_news"]
        registry["read_news"] = Tool(
            stub.name, news_fetcher(settings.news_feed_url), False, stub.doc
        )
    if settings.mcp_server:
        from assistant.adapters import mcp_tools
        from assistant.mcp_client import extend_assistant
        try:
            discovered, invoker = mcp_tools(settings.mcp_server)
            registry = extend_assistant(registry, discovered, invoker)
        except Exception as exc:
            # boot with the builtin tools rather than crash-loop behind a dead
            # MCP server; /health shows the hole
            report("tools", f"MCP discovery failed, builtin tools only: {exc}")

    if settings.ollama_host:
        compose: Composer = fallback_composer(
            model_composer(settings.ollama_host, settings.ollama_model), report
        )
        stream_compose: StreamComposer = fallback_stream(
            model_stream_composer(settings.ollama_host, settings.ollama_model), report
        )
    else:
        compose = offline_compose
        stream_compose = word_stream(offline_compose)

    # outstanding approvals, replay protection and the audit trail share the memory
    # DB, so all three survive a restart with it
    store = settings.assistant_db or ":memory:"

    return Assistant(
        settings=settings, rag=rag, memory=memory, base_registry=registry,
        rec=recorder(otlp_endpoint=settings.otlp_endpoint),
        compose=compose, stream_compose=stream_compose,
        approvals=ApprovalStore(store, settings.approval_ttl_seconds),
        idempotency=IdempotencyStore(store), audit_log=AuditLog(store),
        degraded=degraded,
    )
