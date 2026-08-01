"""Composition settings — one place that reads the environment.

The whole capstone runs offline and deterministic by default. Each real adapter
turns on only when its env var is present, so the fast tier can never accidentally
reach the network and CI stays free:

    ASSISTANT_DB                  -> SQLite-backed memory instead of in-process dict
    QDRANT_URL                    -> QdrantStore instead of the offline BM25 RagStore
    OLLAMA_HOST                   -> Ollama brain instead of the rule-based planner
    MCP_SERVER                    -> discover tools from a real MCP server
    OTEL_EXPORTER_OTLP_ENDPOINT   -> ship spans over OTLP as well as keeping them in memory

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
        )
