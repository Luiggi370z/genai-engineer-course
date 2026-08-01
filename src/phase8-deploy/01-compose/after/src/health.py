"""A health endpoint the platform can ping + structural review of the compose file.

Deployment is only "real" if a stranger can run it. These checks parse the YAML and
inspect the structure — services, pins, healthchecks, dependency conditions, exposed
ports — because a substring match passes on a comment, and a check that passes on a
comment is not a check.
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
    """Every service a reviewer needs, present by name."""
    return [name for name in REQUIRED_SERVICES if name not in services]


def unpinned_images(services: dict) -> list[str]:
    """Services whose image has no tag, or the tag is ':latest'. Built services are
    exempt — their pin is the Dockerfile. ':latest' means every reviewer runs a
    different stack, which is the opposite of reproducible."""
    offenders = []
    for name, spec in services.items():
        image = (spec or {}).get("image")
        if image is None:
            continue
        tag = image.rsplit(":", 1)[1] if ":" in image else ""
        if not tag or tag == "latest":
            offenders.append(name)
    return offenders


def services_without_healthcheck(services: dict) -> list[str]:
    """No healthcheck means `depends_on: service_healthy` has nothing to wait for."""
    return [name for name, spec in services.items() if "healthcheck" not in (spec or {})]


def weak_dependencies(services: dict) -> list[str]:
    """depends_on entries that wait for START instead of HEALTH. The list form
    (`depends_on: [qdrant]`) is always weak; the map form must say
    `condition: service_healthy` — a started Qdrant is not a ready Qdrant."""
    offenders = []
    for name, spec in services.items():
        deps = (spec or {}).get("depends_on")
        if deps is None:
            continue
        if isinstance(deps, list):
            offenders.extend(f"{name} -> {target}" for target in deps)
            continue
        for target, cond in deps.items():
            if (cond or {}).get("condition") != "service_healthy":
                offenders.append(f"{name} -> {target}")
    return offenders


def published_ports(services: dict) -> dict[str, list]:
    """Which services publish ports onto the host at all."""
    return {name: spec["ports"] for name, spec in services.items() if (spec or {}).get("ports")}


def compose_ok(compose_path: str | Path) -> tuple[bool, list[str]]:
    """The whole review at once: (ok, problems). Empty problems == a stack a
    stranger can `docker compose up` and trust."""
    services = load_services(compose_path)
    problems = [f"missing service: {name}" for name in missing_services(services)]
    problems += [f"unpinned image on: {name}" for name in unpinned_images(services)]
    problems += [f"no healthcheck on: {name}" for name in services_without_healthcheck(services)]
    problems += [f"waits for start, not health: {edge}" for edge in weak_dependencies(services)]
    ports = published_ports(services)
    problems += [
        f"{name} publishes {ports[name]} — internal services stay internal"
        for name in ports
        if name != "assistant"
    ]
    if "assistant" not in ports:
        problems.append("assistant publishes no port — nothing is reachable")
    return (not problems, problems)
