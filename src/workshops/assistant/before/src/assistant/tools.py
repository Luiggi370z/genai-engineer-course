"""Workshop 4 layer — the assistant's tools. Every external connection is a tool.

Read-only tools run freely; anything that sends/schedules is gated behind
requires_approval. Connectors are stubbed (email/news/telegram/calendar) so the
whole thing runs offline; swap the bodies for real APIs via env-var credentials.

The judgement to supply here is not the stub bodies — it's the SHAPE of the
registry: which tools are read-only and which are irreversible. Get that wrong
and the whole HITL containment story in agent.py has nothing to stand on.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class Tool:
    name: str
    fn: Callable[..., Any]
    requires_approval: bool
    doc: str


# --- stubbed connectors (read-only) ---
def read_emails(since: str = "today", limit: int = 20) -> list[dict]:
    """Read recent emails (read-only). Use to check or summarize the inbox."""
    # TODO 1: return a small list of email dicts (from/subject/snippet), capped
    # at `limit`. A stub is fine — the point is that it is read-only.
    raise NotImplementedError


def read_news(url: str) -> str:
    """Fetch and return the text of a news page (read-only)."""
    # TODO 2: return some page text. Read-only; no side effects.
    raise NotImplementedError


# --- gated connectors (irreversible) ---
def send_telegram(chat_id: str, message: str) -> dict:
    """Send a Telegram message. IRREVERSIBLE — requires approval."""
    # TODO 3: validate chat_id/message, then return a sent-confirmation dict.
    raise NotImplementedError


def schedule_event(title: str, start_iso: str, duration_min: int = 30) -> dict:
    """Create a calendar event. IRREVERSIBLE — requires approval."""
    # TODO 4: validate title/start_iso, then return a created-event dict.
    raise NotImplementedError


# TODO 5: register all four tools. read_emails/read_news are read-only
# (requires_approval=False); send_telegram/schedule_event are irreversible
# (requires_approval=True). agent.run() reads this map to decide what to gate.
REGISTRY: dict[str, Tool] = {}
