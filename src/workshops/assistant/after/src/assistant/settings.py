"""Composition settings — one place that reads the environment.

The whole capstone runs offline and deterministic by default. Each real adapter
turns on only when its env var is present, so the fast tier can never accidentally
reach the network and CI stays free:

    ASSISTANT_DB                  -> SQLite-backed memory instead of in-process dict
    QDRANT_URL                    -> QdrantStore instead of the offline BM25 RagStore
    OLLAMA_HOST                   -> Ollama brain instead of the rule-based planner
    MCP_SERVER                    -> discover tools from a real MCP server
    OTEL_EXPORTER_OTLP_ENDPOINT   -> ship spans over OTLP as well as keeping them in memory
    ASSISTANT_JWT_SECRET          -> require a Bearer JWT (HS256, shared secret)
    ASSISTANT_JWKS_URL            -> verify RS256 tokens against an issuer's JWKS instead
    ASSISTANT_JWT_ISSUER          -> also require this `iss` claim
    ASSISTANT_JWT_LEEWAY          -> clock-skew tolerance on exp/nbf (default 60s)
    ASSISTANT_APPROVAL_TTL        -> seconds a human approval stays spendable (default 300)
    ASSISTANT_STREAM_MODE         -> "raw" emits chunks before the output gate (local only)
    ASSISTANT_GUARD_MODEL         -> a second-opinion guard model on every untrusted string
    ASSISTANT_EMBED_MODEL         -> real embeddings (via Ollama) instead of the hash vector
    ASSISTANT_PRICE_TIER          -> which price list `make report` costs a run against
    TELEGRAM_BOT_TOKEN            -> send_telegram talks to the real Telegram Bot API
    NEWS_FEED_URL                 -> read_news fetches a real RSS feed (keyless)
    RATE_LIMIT_RPS (+_BURST)      -> token-bucket rate limit on every non-health route
    MAX_CONCURRENCY               -> reject (503) beyond this many in-flight requests
    REQUEST_DEADLINE_SECONDS      -> one budget per request; every layer's timeout fits inside it

Nothing here imports a heavy library; the adapters do that lazily when selected.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from assistant.auth import DEFAULT_LEEWAY, AuthPolicy
from assistant.output_gate import SAFE_BUFFERED


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
    # auth is opt-in so the zero-key demo path keeps working out of the box.
    # A shared secret verifies HS256; a JWKS URL verifies RS256 against the
    # issuer's public keys, which is what an OAuth 2.1 deployment actually does.
    jwt_secret: str | None = None
    jwks_url: str | None = None
    jwt_audience: str = "assistant"
    jwt_issuer: str | None = None
    jwt_leeway: float = DEFAULT_LEEWAY
    # how long a human approval stays spendable — see approvals.py
    approval_ttl_seconds: float = 300.0
    # "safe-buffered" screens before releasing; "raw" emits first — see output_gate.py
    stream_mode: str = SAFE_BUFFERED
    # a model-in-the-loop second opinion on the deterministic screen. Off by
    # default: it costs a round trip per untrusted string, and it can only ever
    # ADD a block — see guard.py for why that direction is not negotiable. Runs
    # on OLLAMA_HOST, so naming a guard model without a host does nothing.
    guard_model: str | None = None
    # which embedder the vector store uses. Unset means `hash_embed`, which is
    # deterministic, offline and NOT semantic: it matches on shared vocabulary,
    # so "reimbursement" will not find a page about "refunds". Naming a model
    # here (nomic-embed-text, mxbai-embed-large) turns the same store into one
    # with real recall. It runs on OLLAMA_HOST, so a model without a host does
    # nothing — and changing it invalidates the collection, which is why
    # QDRANT_COLLECTION exists next to it.
    embed_model: str | None = None
    # which price list `report.py` costs a measured run against (crew.PRICE).
    # "local" is the truth for a self-hosted model — no per-token invoice — and
    # it is also why the cost gate looks free here. Point the composer at a paid
    # API and set this to the tier you actually pay for, or the gate is theatre.
    price_tier: str = "local"
    # real connectors are opt-in for the same reason; the stubs are the default
    telegram_bot_token: str | None = None
    news_feed_url: str | None = None
    # load shedding — off by default so tests and demos can hammer freely
    rate_limit_rps: float | None = None
    rate_limit_burst: float = 10.0
    max_concurrency: int | None = None
    # One budget for the whole request, shared by every layer (deadline.py).
    # Off by default because the fast tier drives a real model in the integration
    # lane and a deadline there would be a flake generator; ON in the deployed
    # profile, where an unbounded request is a worker held hostage. Without it,
    # each layer's timeout composes by ADDITION and the total is a number nobody
    # has ever computed.
    request_deadline: float | None = None

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
            jwks_url=os.getenv("ASSISTANT_JWKS_URL"),
            jwt_audience=os.getenv("ASSISTANT_JWT_AUDIENCE", "assistant"),
            jwt_issuer=os.getenv("ASSISTANT_JWT_ISSUER"),
            jwt_leeway=float(os.getenv("ASSISTANT_JWT_LEEWAY", str(DEFAULT_LEEWAY))),
            approval_ttl_seconds=float(os.getenv("ASSISTANT_APPROVAL_TTL", "300")),
            stream_mode=os.getenv("ASSISTANT_STREAM_MODE", SAFE_BUFFERED),
            guard_model=os.getenv("ASSISTANT_GUARD_MODEL"),
            embed_model=os.getenv("ASSISTANT_EMBED_MODEL"),
            price_tier=os.getenv("ASSISTANT_PRICE_TIER", "local"),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
            news_feed_url=os.getenv("NEWS_FEED_URL"),
            rate_limit_rps=(
                float(rps) if (rps := os.getenv("RATE_LIMIT_RPS")) else None
            ),
            rate_limit_burst=float(os.getenv("RATE_LIMIT_BURST", "10")),
            max_concurrency=(
                int(cc) if (cc := os.getenv("MAX_CONCURRENCY")) else None
            ),
            request_deadline=(
                float(d) if (d := os.getenv("REQUEST_DEADLINE_SECONDS")) else None
            ),
        )

    def auth_policy(self) -> AuthPolicy:
        """The gate's configuration, in one object rather than four arguments
        threaded through every call site — adding `iss` should not mean editing
        api.py."""
        return AuthPolicy(
            secret=self.jwt_secret,
            jwks_url=self.jwks_url,
            audience=self.jwt_audience,
            issuer=self.jwt_issuer,
            leeway=self.jwt_leeway,
        )
