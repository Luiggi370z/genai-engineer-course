"""The real tier. Every test here is @pytest.mark.integration and imports its heavy
library lazily, so the fast gate (`pytest -m "not integration"`) never collects a
missing dependency. Run with:  uv run --group integration pytest -m integration

Each service test skips itself unless its endpoint is configured, so the suite is
green on a laptop with nothing running and meaningful on a machine that has Qdrant,
Ollama, or an MCP server.
"""
import os

import pytest

pytestmark = pytest.mark.integration


def test_qdrant_round_trip():
    pytest.importorskip("qdrant_client")
    url = os.getenv("QDRANT_URL")
    if not url:
        pytest.skip("set QDRANT_URL to run the Qdrant round-trip")

    from assistant.adapters import QdrantStore

    store = QdrantStore(url, collection="assistant_test")
    store.add([
        "the invoice was paid on tuesday",
        "the meeting moved to friday",
    ])
    hits = store.search("invoice", k=1)
    assert hits and "invoice" in hits[0]


def test_qdrant_tenant_filter_isolates_users():
    pytest.importorskip("qdrant_client")
    url = os.getenv("QDRANT_URL")
    if not url:
        pytest.skip("set QDRANT_URL to run the tenant-isolation check")

    from assistant.adapters import QdrantStore

    store = QdrantStore(url, collection="assistant_tenant_test")
    store.add(["alice's contract closes in march"], tenant="alice")
    store.add(["bob's contract closes in june"], tenant="bob")

    alice_hits = store.search("contract closes", k=5, tenant="alice")
    assert alice_hits and all("alice" in h for h in alice_hits), (
        "the server-side payload filter must exclude other tenants"
    )


def test_ollama_generation_adapter():
    pytest.importorskip("ollama")
    host = os.getenv("OLLAMA_HOST")
    if not host:
        pytest.skip("set OLLAMA_HOST to run the Ollama adapter")

    from assistant.adapters import ollama_generate

    out = ollama_generate(
        "Reply with the single word: pong.",
        host=host,
        model=os.getenv("OLLAMA_MODEL", "qwen3.5:9b"),
    )
    assert isinstance(out, str) and out


def test_mcp_server_discovers_and_calls_tools():
    """In-memory MCP client drives the real server — discovery + dispatch, no transport."""
    pytest.importorskip("mcp")
    import anyio
    from mcp import Client

    from assistant.mcp_server import build_server

    async def check() -> None:
        async with Client(build_server()) as c:
            names = {t.name for t in (await c.list_tools()).tools}
            assert {"lookup_fact", "list_topics", "word_count"} <= names
            result = await c.call_tool("lookup_fact", {"topic": "refund window"})
            # content blocks are a union (text/image/audio/resource) — narrow to text
            text = str(getattr(result.content[0], "text", ""))
            assert "five business days" in text.lower()

    anyio.run(check)


def test_discovered_mcp_tools_extend_the_agent_registry():
    """The whole point of mcp_client.py, against the REAL SDK: tools are adapted by
    discovery, not hand-coded — the same path production takes with a URL."""
    pytest.importorskip("mcp")

    from assistant.adapters import mcp_tools
    from assistant.mcp_client import extend_assistant
    from assistant.mcp_server import build_server
    from assistant.tools import REGISTRY

    discovered, invoker = mcp_tools(build_server())
    merged = extend_assistant(dict(REGISTRY), discovered, invoker)
    assert "lookup_fact" in merged and "read_emails" in merged
    out = merged["word_count"].fn(text="one two three")
    assert "3" in str(out)


def test_the_real_telegram_connector_delivers_a_message():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not (token and chat_id):
        pytest.skip("set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to send for real")

    from assistant.connectors import telegram_sender

    result = telegram_sender(token)(chat_id, "capstone integration test ping")
    assert result.get("sent") is True


def test_the_real_news_connector_fetches_a_live_feed():
    feed = os.getenv("NEWS_FEED_URL")
    if not feed:
        pytest.skip("set NEWS_FEED_URL to fetch a live RSS feed")

    from assistant.connectors import news_fetcher

    text = news_fetcher(feed)()
    assert text.startswith("Headlines: ")


def test_the_service_boots_with_real_adapters_when_configured():
    """Proves build_assistant wires the real tier from settings — skipped unless a
    real backend is present, since it would otherwise reach the network."""
    if not (os.getenv("QDRANT_URL") or os.getenv("ASSISTANT_DB")):
        pytest.skip("set QDRANT_URL and/or ASSISTANT_DB to boot the real tier")

    from assistant.service import build_assistant
    from assistant.settings import Settings

    assistant = build_assistant(Settings.from_env())
    tier = assistant.tier()
    if os.getenv("QDRANT_URL"):
        assert tier["rag"] == "qdrant"
    if os.getenv("ASSISTANT_DB"):
        assert tier["memory"] == "sqlite"
