"""Real connectors — env-gated replacements for the stubs in tools.py.

The stubs stay the default so the whole capstone runs with zero keys. When the
env var is present, `build_assistant` swaps the tool BODY and nothing else: the
approval gate on send_telegram and the output re-screen on read_news apply to
the real connector exactly as they did to the stub, because policy lives in the
registry and the hardening wrapper, not in the connector.

Both connectors are stdlib-only (urllib + xml.etree) — no new dependencies for
one HTTP POST and one RSS parse.
"""
from __future__ import annotations

import json
import urllib.request
from collections.abc import Callable
from xml.etree import ElementTree

Sender = Callable[[str, str], dict]


def telegram_sender(bot_token: str, timeout: float = 10.0) -> Sender:
    """A send_telegram body that talks to the real Bot API. Same signature and
    return shape as the stub, so the registry entry (and its approval gate) is
    unchanged."""

    def send(chat_id: str, message: str) -> dict:
        if not chat_id or not message:
            return {"error": "chat_id and message required"}
        request = urllib.request.Request(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            data=json.dumps({"chat_id": chat_id, "text": message}).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = json.loads(response.read())
        except OSError as exc:
            return {"error": f"telegram unreachable: {exc}"}
        return {"sent": bool(body.get("ok")), "chat_id": chat_id}

    return send


def parse_feed(xml_text: str, limit: int = 5) -> str:
    """Turn RSS/Atom XML into the plain-text digest read_news returns. Pure and
    offline-testable; fetch_news is the thin network wrapper around it."""
    root = ElementTree.fromstring(xml_text)
    items = root.iter("item")  # RSS 2.0
    headlines = []
    for item in items:
        title = item.findtext("title") or ""
        if title.strip():
            headlines.append(title.strip())
        if len(headlines) >= limit:
            break
    if not headlines:  # Atom fallback: namespaced <entry><title>
        ns = {"a": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("a:entry", ns):
            title = entry.findtext("a:title", default="", namespaces=ns)
            if title.strip():
                headlines.append(title.strip())
            if len(headlines) >= limit:
                break
    if not headlines:
        return "No headlines found in the feed."
    return "Headlines: " + " | ".join(headlines)


def news_fetcher(feed_url: str, timeout: float = 10.0) -> Callable[..., str]:
    """A read_news body that fetches a real, keyless RSS feed. Read-only, so the
    hardening wrapper re-screens whatever comes back — a poisoned headline is
    contained the same way a poisoned stub is."""

    def fetch(url: str = "") -> str:
        target = url or feed_url
        try:
            with urllib.request.urlopen(target, timeout=timeout) as response:
                return parse_feed(response.read().decode("utf-8", errors="replace"))
        except OSError as exc:
            return f"Feed unreachable: {exc}"

    return fetch
