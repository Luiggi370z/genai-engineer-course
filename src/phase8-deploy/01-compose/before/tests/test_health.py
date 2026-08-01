from pathlib import Path

from src.health import health, required_services_present


def test_health_ok():
    assert health()["status"] == "ok"


def test_compose_wires_the_whole_stack():
    compose = Path(__file__).resolve().parents[1] / "docker-compose.yml"
    assert required_services_present(compose)
