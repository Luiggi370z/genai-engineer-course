"""Trust boundaries — everything that crosses one gets re-screened.

Two channels carry untrusted content into the assistant besides the user's own
message: documents coming back from retrieval, and content coming back from
read-only tools (including tools discovered over MCP). Both are classic
indirect-injection paths, so both are run through the same L1 guardrails
screen as user input before they become evidence.
"""
from __future__ import annotations

from typing import Any

from assistant import guardrails
from assistant.tools import Tool


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


def screen_contexts(docs: list[str]) -> list[str]:
    """Retrieved documents are the classic indirect-injection channel — a poisoned
    page lands in the corpus, retrieval hands it straight to the composer. Every
    document is re-screened before it becomes evidence: an injection-bearing doc
    is DROPPED from the context entirely, PII in a clean one is redacted."""
    kept = []
    for doc in docs:
        ok, cleaned = guardrails.screen(str(doc))
        if ok:
            kept.append(cleaned)
    return kept
