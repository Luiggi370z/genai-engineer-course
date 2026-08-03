"""A health endpoint the platform can ping + structural review of the compose file.

Deployment is only "real" if a stranger can run it. These checks parse the YAML and
inspect the structure — services, pins, healthchecks, dependency conditions, exposed
ports — because a substring match passes on a comment, and a check that passes on a
comment is not a check.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import yaml

REQUIRED_SERVICES = ("assistant", "mcp", "qdrant", "ollama")


def health() -> dict:
    return {"status": "ok"}


class Override(list):
    """A sequence an overlay means to REPLACE rather than extend — `!override`."""


#: `!reset` in an overlay removes the key entirely. A distinct sentinel because
#: `None` is a value compose can legitimately carry.
RESET = object()


class ComposeLoader(yaml.SafeLoader):
    """SafeLoader that knows compose's two merge tags.

    Without these, `yaml.safe_load` raises on a perfectly valid compose file —
    and a reviewer that crashes on the files it is meant to review gets deleted
    rather than fixed.
    """


def _construct_override(loader: ComposeLoader, node: yaml.Node) -> Override:
    return Override(loader.construct_sequence(node))  # pyright: ignore[reportArgumentType]


ComposeLoader.add_constructor("!override", _construct_override)
ComposeLoader.add_constructor("!reset", lambda loader, node: RESET)


def load_services(compose_path: str | Path) -> dict:
    data = yaml.load(Path(compose_path).read_text(), Loader=ComposeLoader)  # noqa: S506
    return data.get("services") or {}


def missing_services(services: dict) -> list[str]:
    """Every service a reviewer needs, present by name."""
    return [name for name in REQUIRED_SERVICES if name not in services]


def image_reference(image: str) -> tuple[str, str]:
    """An image reference split into its tag and its digest, either of which may be
    empty. `name[:tag][@digest]`, and the awkward parts are both real:

    - the digest contains a colon (`@sha256:0bd98f…`), so reading the tag with a
      naive `rsplit(":", 1)` on a digest-pinned image returns the hex and calls it a
      version. It looks pinned, and it is — but a check that cannot tell the two
      apart cannot report which kind of pin it found;
    - a registry host may carry a port (`localhost:5000/qdrant`), so the tag is only
      the colon AFTER the last slash.
    """
    remainder, _, digest = image.partition("@")
    name = remainder.rpartition("/")[2]
    tag = name.rpartition(":")[2] if ":" in name else ""
    return tag, digest


def unpinned_images(services: dict) -> list[str]:
    """Services whose image is not pinned to specific bytes. Built services are
    exempt — their pin is the Dockerfile.

    Pinned means a digest, or a tag that is not ':latest'. The two are not equally
    strong and the ordering matters: ':latest' means every reviewer runs a different
    stack, and a version tag narrows that without closing it, because a tag is a
    mutable pointer its publisher can repoint at a rebuild. Only the digest is a
    content address. This accepts a bare version tag anyway — most of the ecosystem
    ships that way and refusing it would fail every compose file a student has ever
    seen — but the stack it reviews carries both, and so should anything you deploy.
    """
    offenders = []
    for name, spec in services.items():
        image = (spec or {}).get("image")
        if image is None:
            continue
        tag, digest = image_reference(image)
        if not digest and (not tag or tag == "latest"):
            offenders.append(name)
    return offenders


def services_without_healthcheck(services: dict) -> list[str]:
    """No healthcheck means `depends_on: service_healthy` has nothing to wait for."""
    return [name for name, spec in services.items() if "healthcheck" not in (spec or {})]


def cold_model_healthchecks(services: dict) -> list[str]:
    """Services whose healthcheck proves a model is DOWNLOADED but not LOADED.

    `ollama list` is satisfied by a file on disk. Loading a 9B into memory on
    CPU takes minutes and the composer's budget is sixty seconds, so a stack
    that goes healthy on the download alone times out its own first request and
    answers it from the fallback — every probe green, the answer degraded.

    The rule is narrow on purpose: a healthcheck that mentions `ollama list`
    must also depend on something a completed generation produced. It cannot
    tell a warmup sentinel from any other file, which is the honest limit of
    reading a compose file rather than running it; `/ready` on the assistant is
    what proves the round trip.
    """
    offenders = []
    for name, spec in services.items():
        test = (spec or {}).get("healthcheck", {}).get("test")
        probe = " ".join(test) if isinstance(test, list) else str(test or "")
        if "ollama list" in probe and "/tmp/warm" not in probe:
            offenders.append(name)
    return offenders


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


# The base file is a zero-key local demo. The secure overlay is what makes the
# stack safe to expose, so it gets reviewed too — and by the same rule: a control
# that is only present as a commented-out line is not present.
REQUIRED_SECURE_ENV = ("ASSISTANT_JWT_SECRET", "RATE_LIMIT_RPS", "MAX_CONCURRENCY")


def merged_service(base_path: str | Path, overlay_path: str | Path, name: str) -> dict:
    """One service as compose would see it with the overlay applied.

    The rule that surprises everyone, and the reason this function does not just
    call `dict.update`: compose CONCATENATES sequences across files. An overlay
    that narrows `ports` from `8000:8000` to `127.0.0.1:8000:8000` does not
    replace the first with the second, it publishes both — and since the wildcard
    bind already holds the port, the loopback bind fails and the hardened profile
    is the one that will not start. `!override` replaces; `!reset` removes.

    Mappings still merge key-by-key, which is why `environment` behaves the way
    you expect and `ports` does not.
    """
    merged = dict(load_services(base_path).get(name) or {})
    overlay = load_services(overlay_path).get(name) or {}
    for key, value in overlay.items():
        if value is RESET:
            merged.pop(key, None)
        elif isinstance(value, Override):
            merged[key] = list(value)
        elif isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        elif isinstance(value, list) and isinstance(merged.get(key), list):
            merged[key] = [*merged[key], *value]
        else:
            merged[key] = value
    return merged


def container_port(published: str) -> str:
    """The port inside the container from a `[host_ip:][host:]container[/proto]`
    mapping — the part two published entries have to share to be in conflict."""
    return str(published).split("/", 1)[0].rsplit(":", 1)[-1]


def secure_overlay_problems(base_path: str | Path, overlay_path: str | Path) -> list[str]:
    """What the secure profile must actually turn on, checked structurally."""
    assistant = merged_service(base_path, overlay_path, "assistant")
    env = assistant.get("environment") or {}
    problems = [
        f"secure overlay leaves {key} unset" for key in REQUIRED_SECURE_ENV if key not in env
    ]
    secret = str(env.get("ASSISTANT_JWT_SECRET", ""))
    if secret and not secret.startswith("${"):
        # A committed default is not a default, it is a published credential.
        problems.append("ASSISTANT_JWT_SECRET is hard-coded instead of read from the environment")
    ports = assistant.get("ports") or []
    for published in ports:
        if not str(published).startswith(("127.0.0.1:", "localhost:")):
            problems.append(
                f"secure overlay publishes {published} on every interface — bind to loopback"
            )
    # Two mappings for one container port is the signature of an overlay that
    # appended where it meant to replace. It is worth its own message because the
    # symptom is nothing like the cause: the stack fails at `up` with "address
    # already in use" on a port nothing else in it wants.
    seen = Counter(container_port(p) for p in ports)
    problems += [
        f"secure overlay publishes container port {port} twice — compose appended "
        f"its list to the base file's instead of replacing it; tag it `ports: !override`"
        for port, count in sorted(seen.items())
        if count > 1
    ]
    return problems


def compose_ok(compose_path: str | Path) -> tuple[bool, list[str]]:
    """The whole review at once: (ok, problems). Empty problems == a stack a
    stranger can `docker compose up` and trust."""
    services = load_services(compose_path)
    problems = [f"missing service: {name}" for name in missing_services(services)]
    problems += [f"unpinned image on: {name}" for name in unpinned_images(services)]
    problems += [f"no healthcheck on: {name}" for name in services_without_healthcheck(services)]
    problems += [f"waits for start, not health: {edge}" for edge in weak_dependencies(services)]
    problems += [
        f"healthy on a cold model: {name} — the download is not the readiness"
        for name in cold_model_healthchecks(services)
    ]
    ports = published_ports(services)
    problems += [
        f"{name} publishes {ports[name]} — internal services stay internal"
        for name in ports
        if name != "assistant"
    ]
    if "assistant" not in ports:
        problems.append("assistant publishes no port — nothing is reachable")
    return (not problems, problems)
