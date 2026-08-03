from pathlib import Path

from src.health import (
    compose_ok,
    health,
    load_services,
    merged_service,
    missing_services,
    published_ports,
    secure_overlay_problems,
    services_without_healthcheck,
    unpinned_images,
    weak_dependencies,
)

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "docker-compose.yml"
SECURE = ROOT / "docker-compose.secure.yml"

# A compose file with every mistake the checks exist to catch. If the checks pass
# on this, they are matching substrings, not reviewing structure.
BROKEN = """
services:
  assistant:
    build: ./assistant
    depends_on: [qdrant]        # waits for start, not health
  qdrant:
    image: qdrant/qdrant:latest # unpinned
    ports: ["6333:6333"]        # internal service on the host network
"""


def test_health_ok():
    assert health()["status"] == "ok"


def test_every_service_the_stack_needs_is_wired():
    """Three, not four. The model runner moved to the host, where compose cannot
    start it and `depends_on` cannot wait for it — see tests/test_preflight.py
    for the checks that took over that job."""
    assert missing_services(load_services(COMPOSE)) == []


def test_every_pulled_image_is_pinned():
    assert unpinned_images(load_services(COMPOSE)) == []


def test_a_digest_counts_as_pinned_and_a_digests_hex_is_not_a_tag(tmp_path):
    """The stack pins `tag@sha256:…`, which breaks the obvious way to read a tag.

    `"qdrant/qdrant:v1.18.3@sha256:0bd9…".rsplit(":", 1)[1]` is the hex, not the
    version — so a check written that way calls a digest-pinned image pinned by
    accident, and calls `qdrant/qdrant@sha256:0bd9…` pinned for the same wrong
    reason. Both verdicts are right; neither is earned. A registry port is the same
    trap from the other side: the colon in `localhost:5000/qdrant` is not a tag.
    """
    compose = tmp_path / "docker-compose.yml"
    compose.write_text(
        "services:\n"
        "  tag_and_digest:\n"
        "    image: qdrant/qdrant:v1.18.3@sha256:0bd98fa7977f1e75694779359ca4e21\n"
        "  digest_only:\n"
        "    image: qdrant/qdrant@sha256:0bd98fa7977f1e75694779359ca4e21\n"
        "  latest_with_a_digest:\n"  # the digest wins: it names bytes, ':latest' does not
        "    image: qdrant/qdrant:latest@sha256:0bd98fa7977f1e75694779359ca4e21\n"
        "  port_in_the_host_no_tag:\n"
        "    image: localhost:5000/qdrant\n"
        "  port_in_the_host_with_tag:\n"
        "    image: localhost:5000/qdrant:v1.18.3\n"
    )
    assert unpinned_images(load_services(compose)) == ["port_in_the_host_no_tag"]


def test_every_service_has_a_healthcheck():
    assert services_without_healthcheck(load_services(COMPOSE)) == []


def test_dependencies_wait_for_health_not_start():
    assert weak_dependencies(load_services(COMPOSE)) == []


def test_the_assistant_can_resolve_the_host_from_inside_the_network():
    """`host.docker.internal` is free on Docker Desktop and does not exist on
    Linux until it is mapped to the gateway. Without this line the stack builds,
    boots, resolves nothing, and answers every question from the offline
    fallback — the same silent degradation the model runner's healthcheck used
    to guard against from inside the file."""
    assistant = load_services(COMPOSE)["assistant"]
    assert "host.docker.internal:host-gateway" in assistant["extra_hosts"]
    assert "host.docker.internal" in assistant["environment"]["OLLAMA_HOST"]


def test_only_the_assistant_reaches_the_host():
    assert set(published_ports(load_services(COMPOSE))) == {"assistant"}


def test_the_whole_file_passes_review():
    ok, problems = compose_ok(COMPOSE)
    assert ok, problems


def test_the_checks_actually_catch_a_broken_file(tmp_path):
    bad = tmp_path / "docker-compose.yml"
    bad.write_text(BROKEN)
    ok, problems = compose_ok(bad)
    assert not ok
    text = "\n".join(problems)
    assert "missing service" in text  # no mcp
    assert "unpinned image" in text  # :latest
    assert "waits for start" in text  # list-form depends_on
    assert "publishes" in text  # qdrant on the host network
    assert "no healthcheck" in text


# --- the secure profile ---------------------------------------------------------
# The base stack is a zero-key demo and says so. These checks are about the
# overlay you run when the host is reachable by someone other than you.
def test_the_secure_overlay_turns_the_controls_on():
    assert secure_overlay_problems(COMPOSE, SECURE) == []


def test_the_secure_overlay_binds_the_published_port_to_loopback():
    """The base file publishes 8000 on every interface, which is right for a
    laptop and wrong the moment the host has a public IP."""
    ports = merged_service(COMPOSE, SECURE, "assistant")["ports"]
    assert all(str(p).startswith("127.0.0.1:") for p in ports), ports


def test_the_secure_overlay_reads_its_secret_from_the_environment():
    env = merged_service(COMPOSE, SECURE, "assistant")["environment"]
    assert env["ASSISTANT_JWT_SECRET"].startswith("${"), (
        "a committed default is not a default, it is a published credential"
    )


def test_an_overlay_that_narrows_a_list_without_override_is_caught(tmp_path):
    """The bug this closes cost a full end-to-end run before it was understood.

    Compose concatenates sequences across files, so an overlay that "tightens"
    `ports` to loopback publishes BOTH mappings. The wildcard bind takes the port
    first, the loopback bind loses it, and the hardened profile is the only one
    that will not start — reported as "address already in use" on a port nothing
    else in the stack wants. A reviewer that models the overlay as a replacement
    calls this file correct, which is the failure this test exists to prevent."""
    appended = tmp_path / "appended.yml"
    appended.write_text(
        "services:\n"
        "  assistant:\n"
        "    environment:\n"
        "      ASSISTANT_JWT_SECRET: ${ASSISTANT_JWT_SECRET:?set it}\n"
        "      RATE_LIMIT_RPS: '5'\n"
        "      MAX_CONCURRENCY: '4'\n"
        "    ports:\n"
        "      - '127.0.0.1:8000:8000'\n"
    )
    problems = secure_overlay_problems(COMPOSE, appended)
    assert any("twice" in p and "!override" in p for p in problems), problems

    tagged = tmp_path / "tagged.yml"
    tagged.write_text(appended.read_text().replace("ports:", "ports: !override"))
    assert secure_overlay_problems(COMPOSE, tagged) == []


def test_the_secure_checks_catch_an_overlay_that_only_pretends(tmp_path):
    """The same rule as the rest of this file: a control present only as a
    comment is not present, and a check that passes on one is not a check."""
    pretend = tmp_path / "pretend.yml"
    pretend.write_text(
        "services:\n"
        "  assistant:\n"
        "    environment:\n"
        "      # ASSISTANT_JWT_SECRET: turn this on later\n"
        "      ASSISTANT_JWT_SECRET: hunter2-committed-to-git\n"
        "    ports: ['8000:8000']\n"
    )
    problems = secure_overlay_problems(COMPOSE, pretend)
    assert any("RATE_LIMIT_RPS" in p for p in problems)
    assert any("hard-coded" in p for p in problems)
    assert any("every interface" in p for p in problems)
