"""Workshop 2 layer — the assistant's tools. Every external connection is a tool.

Read-only tools run freely; anything that sends/schedules is gated behind
requires_approval. Connectors are stubbed (email/news/telegram/calendar) so the
whole thing runs offline; swap the bodies for real APIs via env-var credentials.
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
    return [
        {"from": "boss@work.com", "subject": "Q3 recap", "snippet": "numbers look good"},
        {"from": "news@digest.com", "subject": "Daily", "snippet": "AI roundup inside"},
    ][:limit]


def read_news(url: str) -> str:
    """Fetch and return the text of a news page (read-only)."""
    return "Headline: local models keep getting smaller and faster. Details..."


# --- gated connectors (irreversible) ---
def send_telegram(chat_id: str, message: str) -> dict:
    """Send a Telegram message. IRREVERSIBLE — requires approval."""
    if not chat_id or not message:
        return {"error": "chat_id and message required"}
    return {"sent": True, "chat_id": chat_id}


def schedule_event(title: str, start_iso: str, duration_min: int = 30) -> dict:
    """Create a calendar event. IRREVERSIBLE — requires approval."""
    if not title or not start_iso:
        return {"error": "title and start_iso required"}
    return {"created": title, "start": start_iso}


REGISTRY: dict[str, Tool] = {
    "read_emails": Tool("read_emails", read_emails, False, read_emails.__doc__ or ""),
    "read_news": Tool("read_news", read_news, False, read_news.__doc__ or ""),
    "send_telegram": Tool("send_telegram", send_telegram, True, send_telegram.__doc__ or ""),
    "schedule_event": Tool("schedule_event", schedule_event, True, schedule_event.__doc__ or ""),
}
