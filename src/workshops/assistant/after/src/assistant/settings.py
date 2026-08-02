"""Composition settings — one place that reads the environment.

The whole capstone runs offline and deterministic by default. Each real adapter
turns on only when its env var is present, so the fast tier can never accidentally
reach the network and CI stays free:

    ASSISTANT_DB                  -> SQLite-backed memory instead of in-process dict
    QDRANT_URL                    -> QdrantStore instead of the offline BM25 RagStore
    OLLAMA_HOST                   -> Ollama brain instead of the rule-based planner
    MCP_SERVER                    -> discover tools from a real MCP server
    OTEL_EXPORTER_OTLP_ENDPOINT   -> ship spans over OTLP as well as keeping them in memory
    ASSISTANT_JWT_SECRET          -> require a Bearer JWT on every mutating endpoint
    TELEGRAM_BOT_TOKEN            -> send_telegram talks to the real Telegram Bot API
    NEWS_FEED_URL                 -> read_news fetches a real RSS feed (keyless)
    RATE_LIMIT_RPS (+_BURST)      -> token-bucket rate limit on every non-health route
    MAX_CONCURRENCY               -> reject (503) beyond this many in-flight requests

Nothing here imports a heavy library; the adapters do that lazily when selected.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    assistant_db: str | None = None
    qdrant_url: str | None = None
    qdrant_collection: str = "assistant"
    ollama_host: str | None = None
    ollama_model: str = "qwen3.5:9b"
    mcp_server: str | None = None
    otlp_endpoint: str | None = None
    context_budget_tokens: int = 120
    # auth is opt-in so the zero-key demo path keeps working out of the box
    jwt_secret: str | None = None
    jwt_audience: str = "assistant"
    # real connectors are opt-in for the same reason; the stubs are the default
    telegram_bot_token: str | None = None
    news_feed_url: str | None = None
    # load shedding — off by default so tests and demos can hammer freely
    rate_limit_rps: float | None = None
    rate_limit_burst: float = 10.0
    max_concurrency: int | None = None

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            assistant_db=os.getenv("ASSISTANT_DB"),
            qdrant_url=os.getenv("QDRANT_URL"),
            qdrant_collection=os.getenv("QDRANT_COLLECTION", "assistant"),
            ollama_host=os.getenv("OLLAMA_HOST"),
            ollama_model=os.getenv("OLLAMA_MODEL", "qwen3.5:9b"),
            mcp_server=os.getenv("MCP_SERVER"),
            otlp_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
            jwt_secret=os.getenv("ASSISTANT_JWT_SECRET"),
            jwt_audience=os.getenv("ASSISTANT_JWT_AUDIENCE", "assistant"),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
            news_feed_url=os.getenv("NEWS_FEED_URL"),
            rate_limit_rps=(
                float(rps) if (rps := os.getenv("RATE_LIMIT_RPS")) else None
            ),
            rate_limit_burst=float(os.getenv("RATE_LIMIT_BURST", "10")),
            max_concurrency=(
                int(cc) if (cc := os.getenv("MAX_CONCURRENCY")) else None
            ),
        )
