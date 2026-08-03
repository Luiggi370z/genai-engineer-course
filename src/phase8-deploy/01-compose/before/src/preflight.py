"""Before the stack starts: is the host's Ollama actually able to answer?

The compose file runs the infrastructure. The models run on your machine, because
Docker Desktop gives containers no GPU and a 9B on CPU inside a VM answers at half
a token per second. That split buys 156x on inference and costs one thing: the
stack now depends on something compose cannot start, cannot see, and cannot wait
for. `depends_on: service_healthy` was doing that work; this module replaces it.

The failure to prevent is not "Ollama is missing" — that one announces itself. It
is the quiet version: everything boots, every probe is green, and every answer
arrives from the offline stitcher because the model was never reachable, or was
reachable but cold. The composer's budget is sixty seconds and loading a 9B takes
longer than that, so a cold model does not error, it times out, and the fallback
covers for it. You find out from a faithfulness score three hours later.

**Readiness is not presence.** `ollama list` is satisfied by a file on disk. The
only evidence that a model can answer is a model answering — so every check below
that could be a lookup should be a round trip instead.

Implement the TODOs, then run `../../../preflight-ollama.sh` against your own
Ollama and make it tell you something true. Reference: ../after/src/preflight.py.

Nothing here may download anything. A preflight that fixes what it finds turns a
six-gigabyte surprise into something that happens silently on someone's tethered
connection; print the exact `ollama pull` and stop.
"""

from __future__ import annotations

import json
import os
import shutil  # noqa: F401 — TODO 7: is docker even here?
import subprocess  # noqa: F401 — TODO 7: the throwaway probe container
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass, field

DEFAULT_CHAT_MODEL = "qwen3.5:9b"
EMBED_MODEL = "nomic-embed-text"
CONTAINER_URL = "http://host.docker.internal:11434"
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
    facts: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)

    def add(self, check: Check) -> Check:
        self.checks.append(check)
        return check


def client_url(env: Mapping[str, str] | None = None) -> str:
    """TODO 1: the URL to TALK to Ollama on, from this host.

    `OLLAMA_HOST` means two different things and the collision is silent. To the
    Ollama server it is a BIND ADDRESS — `OLLAMA_HOST=0.0.0.0:11434` is how CI
    tells the daemon to accept connections from containers. To every client,
    including this script and the assistant, it is a URL to connect to. Pass the
    bind address to a client and it dials 0.0.0.0, which on some stacks is a
    connection refused and on others is worse: it connects to something else.

    Unset -> http://localhost:11434. A value that already looks like a URL passes
    through. Anything else is a bind address: keep the port if it has one (mind
    the bare `0.0.0.0`, which has no colon to split on) and dial loopback.
    """
    raise NotImplementedError


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
    """TODO 2: is anything serving Ollama's API here?

    `GET /api/version`. On any connection failure, return a failing Check whose
    remedy tells the reader to start Ollama — not a traceback.
    """
    raise NotImplementedError


def installed_models(url: str) -> dict[str, str]:
    """TODO 3: tag -> digest for everything pulled (`GET /api/tags`).

    Return the digest, not just the names: a tag is a mutable pointer, so
    "measured against qwen3.5:9b" does not say which qwen3.5:9b.
    """
    raise NotImplementedError


def check_present(tag: str, installed: dict[str, str]) -> Check:
    """TODO 4: is the model on disk?

    Necessary, and — see the module docstring — not sufficient. This check exists
    to produce the `ollama pull` line, not to conclude anything about readiness.
    Two details worth getting right: `ollama pull nomic-embed-text` lists as
    `nomic-embed-text:latest`, and a failure should name what IS installed.
    """
    raise NotImplementedError


def check_chat_warm(url: str, tag: str, timeout: float = WARMUP_TIMEOUT) -> Check:
    """TODO 5: make the model answer. This is the check the others are preamble to.

    `POST /api/generate` with a one-token cap. A pulled model is a file; the
    first request after boot pays the load, and on a cold 9B that load is longer
    than the composer's whole budget — so the stack's first real question times
    out, the offline stitcher answers it, and every probe stays green while the
    answer quality quietly halves.
    """
    raise NotImplementedError


def check_embed_warm(url: str, tag: str = EMBED_MODEL, timeout: float = 60.0) -> Check:
    """TODO 6: the same standard for the embedder, whose failure is quieter still.

    `POST /api/embeddings`, and check the vector is non-empty. A chat model that
    will not load produces a visible timeout; an embedder that will not load
    produces a store that falls to the hash vector and retrieves plausibly on
    shared vocabulary, which only looks wrong when someone asks about
    reimbursements and hears about nothing.
    """
    raise NotImplementedError


def check_container_reachability(timeout: float = 60.0) -> Check:
    """TODO 7: can a CONTAINER reach the host's daemon, or only this shell?

    Everything above ran from the host, where `localhost:11434` is trivially
    reachable. The assistant is not on the host. It resolves
    `host.docker.internal`, which Docker Desktop provides and Linux does not
    until `extra_hosts` maps it to the gateway — and a daemon bound to
    `127.0.0.1` refuses the gateway even when the name resolves.

    One throwaway `docker run --add-host host.docker.internal:host-gateway`
    answers this in advance. Skip it (passing) when docker is not installed:
    there is nothing to boot, so there is nothing to prove.

    Two failures look alike here and mean opposite things. If the probe ran and
    could not reach the host, `REACH_REMEDY` is the right sentence. If docker
    could not reach its own socket, the probe never happened — say so and skip,
    because printing the bind-address remedy would send the reader to reconfigure
    a daemon that is answering perfectly. Not knowing is a third answer.
    """
    raise NotImplementedError


REACH_REMEDY = (
    "bind the daemon to every interface so containers can reach it: stop Ollama, "
    "then `OLLAMA_HOST=0.0.0.0:11434 ollama serve`. On Linux also confirm the "
    "compose file maps host.docker.internal to host-gateway."
)


def run(chat_model: str = DEFAULT_CHAT_MODEL, *, skip_container: bool = False) -> Preflight:
    """TODO 8: every check, in the order that produces the most useful first failure.

    Ordering is a design decision here, not an accident of writing: the daemon
    before the models, presence before warmth, and the container probe last
    because it is the slowest and the least likely. Stop early when a failure
    makes everything after it meaningless — four failures that all restate one
    cause is worse than one sentence. Record the version and both digests in
    `facts` along the way; the attestation reads them.
    """
    raise NotImplementedError


def report(result: Preflight) -> str:
    """TODO 9: the human-readable half.

    Failures carry their remedy, because a preflight that says "model not found"
    and stops has moved the search rather than ended it.
    """
    raise NotImplementedError


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
