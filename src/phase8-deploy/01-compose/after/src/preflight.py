"""Before the stack starts: is the host's Ollama actually able to answer?

The compose file runs the infrastructure. The models run on your machine, because
Docker Desktop gives containers no GPU and a 9B on CPU inside a VM answers at half
a token per second. That split buys 156x on inference and costs one thing: the
stack now depends on something compose cannot start, cannot see, and cannot wait
for. `depends_on: service_healthy` was doing that work; this module replaces it.

The failure it exists to prevent is not "Ollama is missing" — that one announces
itself. It is the quiet version: everything boots, every probe is green, and every
answer arrives from the offline stitcher because the model was never reachable, or
was reachable but cold. The composer's budget is sixty seconds and loading a 9B
takes longer than that, so a cold model does not error, it times out, and the
fallback covers for it. You find out from a faithfulness score three hours later.

**Readiness is not presence, and it never was.** `ollama list` is satisfied by a
file on disk. This module keeps the distinction the compose healthcheck used to
make — that check tested a container that no longer exists, and the idea outlived
it: the only evidence that a model can answer is a model answering. So every check
here that could be a lookup is a round trip instead.

Nothing here downloads anything. A preflight that fixes what it finds turns a
six-gigabyte surprise into something that happens silently on someone's tethered
connection; it prints the exact `ollama pull` and stops.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass, field

#: What the stack needs on the host, and why each one. The chat tag is
#: overridable because CI runs a smaller one; the embedder is not, because the
#: collection name is derived from it and the semantic-recall check depends on it.
DEFAULT_CHAT_MODEL = "qwen3.5:9b"
EMBED_MODEL = "nomic-embed-text"

#: Where the assistant reaches the host from inside the compose network. Only ever
#: a URL — see `client_url` for the trap this constant is half of.
CONTAINER_URL = "http://host.docker.internal:11434"

#: How long a warmup may take. A cold 9B on a GPU loads in seconds; this is
#: generous enough for a laptop that is also compiling something, and short
#: enough that a genuinely stuck daemon is not mistaken for a slow one.
WARMUP_TIMEOUT = 300.0


@dataclass
class Check:
    """One question, its answer, and what to type if the answer is no."""

    name: str
    ok: bool
    detail: str
    remedy: str = ""


@dataclass
class Preflight:
    checks: list[Check] = field(default_factory=list)
    #: Version and digests, for the attestation. A run that says "passed against
    #: qwen3.5:9b" without saying WHICH qwen3.5:9b has not said much: tags are
    #: mutable and a re-pull can change the bytes under a name.
    facts: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)

    def add(self, check: Check) -> Check:
        self.checks.append(check)
        return check


def client_url(env: dict[str, str] | None = None) -> str:
    """The URL to TALK to Ollama on, from this host.

    `OLLAMA_HOST` means two different things and the collision is silent. To the
    Ollama server it is a BIND ADDRESS — `OLLAMA_HOST=0.0.0.0:11434` is how CI
    tells the daemon to accept connections from containers. To every client,
    including this script and the assistant, it is a URL to connect to. Pass the
    bind address to a client and it dials 0.0.0.0, which on some stacks is a
    connection refused and on others is worse: it connects to something else.

    So a value that is not a URL is treated as the server-side meaning it must
    have been, and the loopback address is used to reach it.
    """
    source: Mapping[str, str] = os.environ if env is None else env
    raw = (source.get("OLLAMA_HOST") or "").strip()
    if not raw:
        return "http://localhost:11434"
    if not raw.startswith(("http://", "https://")):
        # A bind address, not a URL. `0.0.0.0` means "every interface", which is
        # not an address you dial; the port is the part worth keeping — and only
        # if there is one, since a bare `0.0.0.0` has no colon to split on and
        # would otherwise be read as its own port number.
        tail = raw.rpartition(":")[2]
        port = tail if tail.isdigit() else "11434"
        return f"http://localhost:{port}"
    return raw


def _get(url: str, path: str, timeout: float = 5.0) -> dict:
    with urllib.request.urlopen(f"{url.rstrip('/')}{path}", timeout=timeout) as response:  # noqa: S310
        return json.loads(response.read())


def _post(url: str, path: str, payload: dict, timeout: float) -> dict:
    request = urllib.request.Request(  # noqa: S310
        f"{url.rstrip('/')}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return json.loads(response.read())


def check_daemon(url: str) -> Check:
    """Is anything serving Ollama's API here?"""
    try:
        version = _get(url, "/api/version").get("version", "unknown")
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return Check(
            "daemon",
            False,
            f"no Ollama at {url}: {exc}",
            "start it with `ollama serve` (or open the Ollama app), then re-run",
        )
    return Check("daemon", True, f"Ollama {version} at {url}")


def installed_models(url: str) -> dict[str, str]:
    """Tag -> digest for everything pulled, as `ollama list` would report it.

    The digest is why this returns a mapping rather than a set: it is the only
    part of a model's identity that a re-pull cannot change under you.
    """
    models = _get(url, "/api/tags").get("models") or []
    return {m["name"]: str(m.get("digest", ""))[:19] for m in models if m.get("name")}


def _matches(tag: str, installed: dict[str, str]) -> str | None:
    """The installed name for `tag`, allowing for Ollama's implicit `:latest`."""
    for candidate in (tag, f"{tag}:latest", tag.removesuffix(":latest")):
        if candidate in installed:
            return candidate
    return None


def check_present(tag: str, installed: dict[str, str]) -> Check:
    """Is the model on disk? Necessary, and — see the module docstring — not
    sufficient. This check exists to produce the `ollama pull` line, not to
    conclude anything about readiness."""
    name = _matches(tag, installed)
    if name is None:
        have = ", ".join(sorted(installed)) or "nothing"
        return Check(
            f"present:{tag}",
            False,
            f"{tag} is not pulled (installed: {have})",
            f"ollama pull {tag}",
        )
    return Check(f"present:{tag}", True, f"{tag} present ({installed[name]})")


def check_chat_warm(url: str, tag: str, timeout: float = WARMUP_TIMEOUT) -> Check:
    """Make the model answer. This is the check the others are preamble to.

    A pulled model is a file. The first request after boot pays the load, and on
    a cold 9B that load is longer than the composer's whole budget — so the
    stack's first real question times out, the offline stitcher answers it, and
    every probe stays green while the answer quality quietly halves. Paying the
    load here means the readiness signal and the truth agree, and it means the
    number in a release report describes the model it names.
    """
    started = time.monotonic()
    try:
        response = _post(
            url,
            "/api/generate",
            {"model": tag, "prompt": "ok", "stream": False, "options": {"num_predict": 1}},
            timeout,
        )
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return Check(
            f"warm:{tag}",
            False,
            f"{tag} did not complete a generation: {exc}",
            f"try `ollama run {tag} ok` and watch for an out-of-memory or disk error",
        )
    elapsed = time.monotonic() - started
    if not str(response.get("response", "")).strip() and not response.get("done"):
        return Check(f"warm:{tag}", False, f"{tag} returned nothing", f"ollama run {tag} ok")
    return Check(f"warm:{tag}", True, f"{tag} answered in {elapsed:.1f}s and is resident")


def check_embed_warm(url: str, tag: str = EMBED_MODEL, timeout: float = 60.0) -> Check:
    """The same standard for the embedder, whose failure is quieter still.

    A chat model that will not load produces a visible timeout. An embedder that
    will not load produces an ingest that half-finishes, or a store that falls to
    the hash vector — which retrieves, plausibly, on shared vocabulary, and only
    looks wrong when someone asks about reimbursements and hears about nothing.
    """
    try:
        vector = _post(url, "/api/embeddings", {"model": tag, "prompt": "ok"}, timeout).get(
            "embedding"
        )
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return Check(
            f"warm:{tag}",
            False,
            f"{tag} did not return a vector: {exc}",
            f"ollama pull {tag}",
        )
    if not vector:
        return Check(f"warm:{tag}", False, f"{tag} returned an empty vector", f"ollama pull {tag}")
    return Check(f"warm:{tag}", True, f"{tag} embeds ({len(vector)} dimensions)")


def check_container_reachability(timeout: float = 60.0) -> Check:
    """Can a CONTAINER reach the host's daemon, or only this shell?

    Everything above ran from the host, where `localhost:11434` is trivially
    reachable. The assistant is not on the host. It resolves
    `host.docker.internal`, which Docker Desktop provides and Linux does not
    until `extra_hosts` maps it to the gateway — and a daemon bound to
    `127.0.0.1` refuses the gateway even when the name resolves.

    Both of those fail in exactly the way this whole module is about: the
    assistant boots, `/health` is green, and every answer comes from the
    fallback. One throwaway container answers the question in advance.
    """
    if not shutil.which("docker"):
        return Check("container->host", True, "docker not installed; skipping (nothing to boot)")
    try:
        result = subprocess.run(  # noqa: S603
            [
                "docker", "run", "--rm",
                "--add-host", "host.docker.internal:host-gateway",
                "curlimages/curl:8.11.1",
                "--silent", "--show-error", "--max-time", "10",
                f"{CONTAINER_URL}/api/version",
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return Check("container->host", False, f"probe container failed: {exc}", REACH_REMEDY)
    if result.returncode != 0:
        stderr = result.stderr.strip()
        # "Could not ask" is not "asked and got no". If Docker itself never ran the
        # probe, blaming Ollama's bind address sends the reader to fix a daemon that
        # is answering perfectly — the exact misdiagnosis this module exists to stop.
        # Compose is about to fail on the same wall with a clearer message, so skip.
        if _docker_is_unreachable(stderr):
            return Check("container->host", True, f"docker is not usable here; skipping ({stderr})")
        return Check(
            "container->host",
            False,
            f"a container cannot reach {CONTAINER_URL}: {stderr}",
            REACH_REMEDY,
        )
    return Check("container->host", True, f"a container reaches {CONTAINER_URL}")


def _docker_is_unreachable(stderr: str) -> bool:
    """Did docker fail to talk to its own daemon, rather than report a verdict?"""
    lowered = stderr.lower()
    return any(
        phrase in lowered
        for phrase in (
            "cannot connect to the docker daemon",
            "error during connect",
            "docker daemon is not running",
            "permission denied while trying to connect",
        )
    )


REACH_REMEDY = (
    "bind the daemon to every interface so containers can reach it: stop Ollama, "
    "then `OLLAMA_HOST=0.0.0.0:11434 ollama serve`. On Linux also confirm the "
    "compose file maps host.docker.internal to host-gateway."
)


def run(chat_model: str = DEFAULT_CHAT_MODEL, *, skip_container: bool = False) -> Preflight:
    """Every check, in the order that produces the most useful first failure.

    Ordering is a design decision here, not an accident of writing: the daemon
    before the models, presence before warmth, and the container probe last
    because it is the slowest and the least likely. A learner should read one
    sentence and know what to type.
    """
    result = Preflight()
    url = client_url()

    daemon = result.add(check_daemon(url))
    if not daemon.ok:
        return result
    result.facts["ollama_version"] = daemon.detail.split()[1]
    result.facts["ollama_url"] = url

    installed = installed_models(url)
    present = [result.add(check_present(tag, installed)) for tag in (chat_model, EMBED_MODEL)]
    if not all(check.ok for check in present):
        return result
    for tag in (chat_model, EMBED_MODEL):
        name = _matches(tag, installed) or tag
        result.facts[f"digest:{tag}"] = installed[name]

    result.add(check_chat_warm(url, chat_model))
    result.add(check_embed_warm(url))
    if not skip_container:
        result.add(check_container_reachability())
    return result


def report(result: Preflight) -> str:
    """The human-readable half. The failures carry the remedy, because a preflight
    that says "model not found" and stops has moved the search, not ended it."""
    lines = [("  ok   " if c.ok else "  FAIL ") + c.detail for c in result.checks]
    lines += [f"       -> {c.remedy}" for c in result.checks if not c.ok and c.remedy]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Check the host's Ollama before the stack boots.")
    parser.add_argument("--model", default=os.getenv("OLLAMA_MODEL") or DEFAULT_CHAT_MODEL)
    parser.add_argument("--skip-container", action="store_true")
    parser.add_argument("--json", dest="json_path", help="write the version/digest record here")
    args = parser.parse_args(argv)

    result = run(args.model, skip_container=args.skip_container)
    print(report(result))
    if args.json_path:
        from pathlib import Path

        Path(args.json_path).write_text(json.dumps(result.facts, indent=2, sort_keys=True))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
