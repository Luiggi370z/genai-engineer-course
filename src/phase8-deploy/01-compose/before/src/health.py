"""A health endpoint the platform can ping + structural review of the compose file.

Deployment is only "real" if a stranger can run it. Your checks parse the YAML and
inspect the structure — services, pins, healthchecks, dependency conditions, exposed
ports — because a substring match passes on a comment, and a check that passes on a
comment is not a check.

Implement the TODOs, watch them fail on this lesson's docker-compose.yml, then fix
the compose file until the whole suite is green. Reference: ../after/src/health.py.
"""
from __future__ import annotations

from pathlib import Path

import yaml

REQUIRED_SERVICES = ("assistant", "mcp", "qdrant", "ollama")


def health() -> dict:
    return {"status": "ok"}


def load_services(compose_path: str | Path) -> dict:
    data = yaml.safe_load(Path(compose_path).read_text())
    return data.get("services") or {}


def missing_services(services: dict) -> list[str]:
    """TODO 1: every name in REQUIRED_SERVICES that the compose file lacks."""
    raise NotImplementedError


def unpinned_images(services: dict) -> list[str]:
    """TODO 2: services whose image has no tag, or the tag is ':latest'. Built
    services (a `build:` key, no `image:`) are exempt — their pin is the Dockerfile."""
    raise NotImplementedError


def services_without_healthcheck(services: dict) -> list[str]:
    """TODO 3: services with no healthcheck. Without one,
    `depends_on: service_healthy` has nothing to wait for."""
    raise NotImplementedError


def weak_dependencies(services: dict) -> list[str]:
    """TODO 4: every depends_on edge that waits for START instead of HEALTH, as
    "name -> target" strings. The list form (`depends_on: [qdrant]`) is always weak;
    the map form must say `condition: service_healthy`."""
    raise NotImplementedError


def published_ports(services: dict) -> dict[str, list]:
    """TODO 5: {service: ports} for every service that publishes onto the host."""
    raise NotImplementedError


def compose_ok(compose_path: str | Path) -> tuple[bool, list[str]]:
    """TODO 6: the whole review at once — (ok, problems). Missing services, unpinned
    images, missing healthchecks, weak dependencies, any published port that isn't
    the assistant's, and an assistant that publishes nothing at all."""
    raise NotImplementedError
