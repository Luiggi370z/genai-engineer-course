"""A health endpoint the platform can ping + a compose-sanity checker.

Deployment is only 'real' if a stranger can run it: this validates that the compose
file wires the services a reviewer needs, and gives you a /health payload.
"""
from __future__ import annotations

from pathlib import Path


def health() -> dict:
    return {"status": "ok"}


def compose_has_service(compose_text: str, service: str) -> bool:
    return f"\n  {service}:" in compose_text


def required_services_present(compose_path: str | Path) -> bool:
    text = Path(compose_path).read_text()
    return all(compose_has_service(text, s) for s in ("assistant", "mcp", "qdrant", "ollama"))
