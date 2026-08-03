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

#: The model runner is not in here, and that is the point: it runs on the host,
#: where compose can neither start it nor wait for it. src/preflight.py is where
#: you check it.
REQUIRED_SERVICES = ("assistant", "mcp", "qdrant")


def health() -> dict:
    return {"status": "ok"}


def load_services(compose_path: str | Path) -> dict:
    # TODO 9: `safe_load` raises on `!override` and `!reset`, compose's two merge
    # tags — and you will need `!override` in the secure overlay (see TODO 7).
    # Teach a SafeLoader subclass about both rather than dropping to `yaml.load`
    # with the default loader: a reviewer that executes arbitrary tags in a file
    # it was handed to review is its own security lesson.
    data = yaml.safe_load(Path(compose_path).read_text())
    return data.get("services") or {}


def missing_services(services: dict) -> list[str]:
    """TODO 1: every name in REQUIRED_SERVICES that the compose file lacks."""
    raise NotImplementedError


def unpinned_images(services: dict) -> list[str]:
    """TODO 2: services whose image is not pinned to specific bytes. Built services
    (a `build:` key, no `image:`) are exempt — their pin is the Dockerfile.

    Pinned means a digest (`name@sha256:…`) or a tag that is not ':latest'. Parse the
    reference as `name[:tag][@digest]` and mind two colons that are not tag
    separators: the one inside the digest, and the one in a registry port
    (`localhost:5000/qdrant`). Reading the tag with `rsplit(":", 1)` finds the digest
    hex on one and the port on the other."""
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


# The base file is a zero-key local demo. The secure overlay is what makes the
# stack safe to expose, so it gets reviewed too — and by the same rule: a control
# that is only present as a commented-out line is not present.
REQUIRED_SECURE_ENV = ("ASSISTANT_JWT_SECRET", "RATE_LIMIT_RPS", "MAX_CONCURRENCY")


def merged_service(base_path: str | Path, overlay_path: str | Path, name: str) -> dict:
    """TODO 7: one service as compose would see it with the overlay applied.

    Mappings merge key-by-key, so `environment` behaves the way you expect.
    Sequences do NOT: compose CONCATENATES them across files. Model that, however
    much it feels like a bug — because the whole point of this function is to tell
    you what will actually run, and "overlay keys win" is a comfortable model that
    would have you sign off on a profile that cannot start.

    Then look at docker-compose.secure.yml with that rule in mind. Narrowing
    `8000:8000` to `127.0.0.1:8000:8000` publishes both; the wildcard bind takes
    the port, the loopback bind fails, and the HARDENED profile is the only one
    that will not boot — reported as "address already in use" on a port nothing
    else in the stack wants. `!override` replaces the list; `!reset` removes it.
    """
    raise NotImplementedError


def secure_overlay_problems(base_path: str | Path, overlay_path: str | Path) -> list[str]:
    """TODO 8: what the secure profile must actually turn on. Every name in
    REQUIRED_SECURE_ENV set on the merged assistant; ASSISTANT_JWT_SECRET read from
    the environment (`${...}`) rather than hard-coded; every published port bound
    to loopback; and no container port published twice, which is the signature of
    an overlay that appended where it meant to replace. Give that last one its own
    message — the symptom is nothing like the cause, and a reviewer that only says
    "publishes 0.0.0.0:8000" sends the reader to the wrong file.

    Then fix docker-compose.secure.yml until this returns []."""
    raise NotImplementedError


def compose_ok(compose_path: str | Path) -> tuple[bool, list[str]]:
    """TODO 6: the whole review at once — (ok, problems). Missing services, unpinned
    images, missing healthchecks, weak dependencies, cold-model healthchecks, any
    published port that isn't the assistant's, and an assistant that publishes
    nothing at all."""
    raise NotImplementedError
