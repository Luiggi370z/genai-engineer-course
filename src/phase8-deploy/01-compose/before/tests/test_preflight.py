"""The host checks, and the one idea they inherited from the compose file.

`cold_model_healthchecks` used to live in health.py and read the `ollama`
service's healthcheck, looking for a probe that was satisfied by a download. That
service is gone — the model runs on the host now — but the mistake it caught is
not, so the rule moved here and got sharper on the way: reading a compose file
could only ask whether someone had WRITTEN a warmup, while this can ask the
daemon whether the model actually answers.

No network in any of these. `installed_models` and the two warmups are the only
functions that touch a socket, and each takes its URL as an argument.
"""

import json

import pytest

from src import preflight
from src.preflight import Check, Preflight, check_present, client_url, report

WARM = Check("daemon", True, "Ollama 0.32.5 at http://localhost:11434")


def _daemon_up(url):
    return Check("daemon", True, f"Ollama 0.32.5 at {url}")


def _chat_warm(url, tag, **kwargs):
    return Check(f"warm:{tag}", True, "warm")


def _embed_warm(url, **kwargs):
    return Check("warm:embed", True, "warm")


# --- readiness is not presence, moved from the compose healthcheck --------------


def test_a_model_that_is_merely_present_is_not_yet_a_model_that_can_answer():
    """The migrated lesson, and the reason presence and warmth are two checks.

    A downloaded model is a file on disk. Loading a 9B takes longer than the
    composer's whole sixty-second budget, so a stack that treats the download as
    readiness times out its own first question and answers it from the offline
    fallback — every probe green, the answer degraded. `check_present` therefore
    concludes nothing about readiness; it exists to produce the `ollama pull`
    line. Only a completed generation settles the question.
    """
    installed = {"qwen3.5:9b": "sha256:abc", "nomic-embed-text:latest": "sha256:def"}
    assert check_present("qwen3.5:9b", installed).ok

    # ...and the run does not stop there. The warmup is a separate check, against
    # the daemon, precisely because this one cannot see memory.
    names = [c.name for c in _all_checks_for(installed)]
    assert "present:qwen3.5:9b" in names
    assert "warm:qwen3.5:9b" in names, "presence alone must never be the last word"
    assert names.index("present:qwen3.5:9b") < names.index("warm:qwen3.5:9b")


def test_a_download_that_never_happened_is_caught_with_the_command_to_fix_it():
    """The other half of the old pair. A missing model used to surface twenty
    minutes in as a composer timeout; here it is one line and a command."""
    absent = check_present("qwen3.5:9b", {"nomic-embed-text:latest": "sha256:def"})
    assert not absent.ok
    assert absent.remedy == "ollama pull qwen3.5:9b"
    assert "nomic-embed-text:latest" in absent.detail, "say what IS installed, not just what isn't"


def test_ollamas_implicit_latest_tag_is_not_a_missing_model():
    """`ollama pull nomic-embed-text` lists as `nomic-embed-text:latest`. Reading
    that as absent sends a learner to re-pull a model they already have."""
    assert check_present("nomic-embed-text", {"nomic-embed-text:latest": "sha256:def"}).ok
    assert check_present("qwen3.5:9b", {"qwen3.5:9b": "sha256:abc"}).ok


# --- OLLAMA_HOST means two different things ------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, "http://localhost:11434"),
        # Bind addresses. CI sets this so containers can reach the daemon; a
        # client that dials 0.0.0.0 is not talking to the same thing.
        ("0.0.0.0:11434", "http://localhost:11434"),
        ("127.0.0.1:11434", "http://localhost:11434"),
        ("0.0.0.0", "http://localhost:11434"),
        # A real client URL passes through untouched.
        ("http://host.docker.internal:11434", "http://host.docker.internal:11434"),
        ("http://localhost:9999", "http://localhost:9999"),
    ],
)
def test_a_bind_address_is_never_dialled_as_a_url(value, expected):
    """To the server `OLLAMA_HOST` is where to LISTEN; to every client it is where
    to CONNECT. The names are identical and the meanings do not overlap, so the
    one value has to be read for which side is asking."""
    env = {} if value is None else {"OLLAMA_HOST": value}
    assert client_url(env) == expected


# --- the report is the product -------------------------------------------------


def test_every_failure_arrives_with_the_command_that_fixes_it():
    """A preflight that says "model not found" and stops has moved the search
    rather than ended it."""
    missing = Check(
        "present:qwen3.5:9b", False, "qwen3.5:9b is not pulled", "ollama pull qwen3.5:9b"
    )
    result = Preflight(checks=[WARM, missing])
    assert not result.ok
    text = report(result)
    assert "FAIL" in text
    assert "-> ollama pull qwen3.5:9b" in text


def test_a_clean_run_records_the_version_and_the_digests(monkeypatch, tmp_path):
    """"Passed against qwen3.5:9b" does not say WHICH qwen3.5:9b. Tags are mutable
    pointers, so a re-pull can change the bytes under a name that a release report
    claims to have measured. The digest is what makes the claim checkable."""
    monkeypatch.setattr(preflight, "check_daemon", _daemon_up)
    monkeypatch.setattr(
        preflight,
        "installed_models",
        lambda url: {"qwen3.5:9b": "sha256:abc123", "nomic-embed-text:latest": "sha256:def456"},
    )
    monkeypatch.setattr(preflight, "check_chat_warm", _chat_warm)
    monkeypatch.setattr(preflight, "check_embed_warm", _embed_warm)

    facts_path = tmp_path / "facts.json"
    assert preflight.main(["--skip-container", "--json", str(facts_path)]) == 0

    facts = json.loads(facts_path.read_text())
    assert facts["ollama_version"] == "0.32.5"
    assert facts["digest:qwen3.5:9b"] == "sha256:abc123"
    assert facts["digest:nomic-embed-text"] == "sha256:def456"


def test_a_missing_daemon_stops_before_asking_about_models(monkeypatch):
    """Ordering is a design decision: one useful sentence beats four failures that
    all restate the same cause."""
    monkeypatch.setattr(
        preflight, "check_daemon", lambda url: Check("daemon", False, "no Ollama", "ollama serve")
    )
    monkeypatch.setattr(
        preflight,
        "installed_models",
        lambda url: pytest.fail("asked about models with no daemon to ask"),
    )
    result = preflight.run(skip_container=True)
    assert not result.ok
    assert [c.name for c in result.checks] == ["daemon"]


def test_the_preflight_never_pulls_anything(monkeypatch):
    """Six gigabytes on someone's tethered connection is not a fix, it is a
    surprise. Checked by watching every request the run makes, on the exact input
    that would tempt a helpful implementation: a model that is missing.
    """
    requested: list[str] = []

    def record_get(url, path, timeout=5.0):
        requested.append(path)
        return {"version": "0.32.5", "models": []}

    def record_post(url, path, payload, timeout):
        requested.append(path)
        return {}

    monkeypatch.setattr(preflight, "_get", record_get)
    monkeypatch.setattr(preflight, "_post", record_post)

    result = preflight.run("qwen3.5:9b", skip_container=True)

    assert not result.ok, "a missing model has to fail rather than be fetched"
    assert not any("pull" in path for path in requested), requested


def _all_checks_for(installed: dict[str, str]) -> list[Check]:
    """The checks `run` would perform, without a daemon to perform them against."""
    from unittest import mock

    with (
        mock.patch.object(preflight, "check_daemon", _daemon_up),
        mock.patch.object(preflight, "installed_models", lambda url: installed),
        mock.patch.object(preflight, "check_chat_warm", _chat_warm),
        mock.patch.object(preflight, "check_embed_warm", _embed_warm),
    ):
        return preflight.run(skip_container=True).checks
