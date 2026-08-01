"""TODO: a /health endpoint + a compose-sanity checker.

- health(): return {"status": "ok"}.
- required_services_present(path): True only if the compose file wires
  assistant, mcp, qdrant, AND ollama (so a reviewer can run everything).

Reference: ../after/src/health.py.
"""
from __future__ import annotations

from pathlib import Path


def health() -> dict:
    raise NotImplementedError  # TODO 1


def required_services_present(compose_path: str | Path) -> bool:
    raise NotImplementedError  # TODO 2
