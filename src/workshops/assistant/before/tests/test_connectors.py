"""The real connectors, offline: the feed parser is pure, the Telegram sender's
HTTP call is monkeypatched, and the wiring test proves build_assistant swaps the
tool BODY while the approval gate and hardening stay exactly where they were."""

import io
import json

import assistant.connectors as connectors
from assistant.connectors import news_fetcher, parse_feed, telegram_sender
from assistant.service import build_assistant
from assistant.settings import Settings

RSS = """<?xml version="1.0"?>
<rss version="2.0"><channel><title>Feed</title>
<item><title>Local models keep shrinking</title></item>
<item><title>Vector DBs grow up</title></item>
<item><title>Agents meet production</title></item>
</channel></rss>"""

ATOM = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<entry><title>Atom headline one</title></entry>
<entry><title>Atom headline two</title></entry>
</feed>"""


def test_the_parser_reads_rss_headlines_in_order():
    text = parse_feed(RSS)
    assert text.startswith("Headlines: ")
    assert text.index("shrinking") < text.index("grow up") < text.index("production")


def test_the_parser_respects_the_limit():
    assert parse_feed(RSS, limit=1).count("|") == 0


def test_the_parser_falls_back_to_atom():
    assert "Atom headline one" in parse_feed(ATOM)


def test_an_empty_feed_degrades_to_a_message_not_a_crash():
    assert "No headlines" in parse_feed("<rss version='2.0'><channel/></rss>")


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_the_telegram_sender_posts_to_the_bot_api(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout=0):
        seen["url"] = request.full_url
        seen["payload"] = json.loads(request.data)
        return FakeResponse(b'{"ok": true}')

    monkeypatch.setattr(connectors.urllib.request, "urlopen", fake_urlopen)
    result = telegram_sender("TOKEN123")("team-chat", "deploy done")
    assert result == {"sent": True, "chat_id": "team-chat"}
    assert "botTOKEN123/sendMessage" in seen["url"]
    assert seen["payload"] == {"chat_id": "team-chat", "text": "deploy done"}


def test_the_telegram_sender_reports_network_failure_as_a_result(monkeypatch):
    def refuse(request, timeout=0):
        raise OSError("connection refused")

    monkeypatch.setattr(connectors.urllib.request, "urlopen", refuse)
    result = telegram_sender("TOKEN123")("team-chat", "hello")
    assert "unreachable" in result["error"]


def test_the_news_fetcher_returns_parsed_headlines(monkeypatch):
    monkeypatch.setattr(
        connectors.urllib.request, "urlopen",
        lambda url, timeout=0: FakeResponse(RSS.encode()),
    )
    assert "shrinking" in news_fetcher("https://example.com/feed.xml")()


def test_env_gated_connectors_swap_the_body_but_keep_the_gate():
    stubbed = build_assistant(Settings())
    real = build_assistant(
        Settings(telegram_bot_token="TOKEN123", news_feed_url="https://example.com/f.xml")
    )
    # the bodies changed...
    assert real.base_registry["send_telegram"].fn is not stubbed.base_registry["send_telegram"].fn
    assert real.base_registry["read_news"].fn is not stubbed.base_registry["read_news"].fn
    # ...but the policy did not: sends still need approval, reads still don't
    assert real.base_registry["send_telegram"].requires_approval is True
    assert real.base_registry["read_news"].requires_approval is False
    assert real.tier()["connectors"] == "real"
