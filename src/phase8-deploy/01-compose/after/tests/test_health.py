from pathlib import Path

from src.health import (
    compose_ok,
    health,
    load_services,
    missing_services,
    published_ports,
    services_without_healthcheck,
    unpinned_images,
    weak_dependencies,
)

COMPOSE = Path(__file__).resolve().parents[1] / "docker-compose.yml"

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


def test_all_four_services_are_wired():
    assert missing_services(load_services(COMPOSE)) == []


def test_every_pulled_image_is_pinned():
    assert unpinned_images(load_services(COMPOSE)) == []


def test_every_service_has_a_healthcheck():
    assert services_without_healthcheck(load_services(COMPOSE)) == []


def test_dependencies_wait_for_health_not_start():
    assert weak_dependencies(load_services(COMPOSE)) == []


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
    assert "missing service" in text        # no mcp, no ollama
    assert "unpinned image" in text         # :latest
    assert "waits for start" in text        # list-form depends_on
    assert "publishes" in text              # qdrant on the host network
    assert "no healthcheck" in text
