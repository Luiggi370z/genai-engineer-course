"""Trust boundaries — everything that crosses one gets re-screened.

Two channels carry untrusted content into the assistant besides the user's own
message: documents coming back from retrieval, and content coming back from
read-only tools (including tools discovered over MCP). Both are classic
indirect-injection paths, so both are run through the same L1 guardrails
screen as user input before they become evidence.
"""
from __future__ import annotations

from assistant import guardrails
from assistant.tools import Tool


def harden_registry(registry: dict[str, Tool]) -> dict[str, Tool]:
    """TODO 1: re-screen the OUTPUT of every read-only tool with guardrails.screen()
    — a fetched email/page is exactly where an indirect injection arrives, and
    MCP-discovered tools take this path too. Leave the irreversible
    (requires_approval) tools alone; the agent's approval gate covers those.
    Return a NEW registry; do not mutate the originals."""
    raise NotImplementedError


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
