"""TODO: the release lane — publish, deploy, prove, and undo.

`observe.py` answers "is it healthy?". This answers the four questions around it,
and each one exists because of a specific way a deploy goes wrong at 2am:

1. **What exactly is running?** `image_ref` / `is_immutable`. A tag like `latest`
   is a name, not a version — roll back to it and you get the code you just
   rolled back FROM, because the tag moved with you.
2. **Where do the secrets live?** `render_manifest` / `leaked_secrets`. A
   manifest is a file in git. Once a key's value is in it, the key is in the
   history forever and rotating it is the only remedy.
3. **Did it actually work?** `smoke` / `passed`. "The deploy exited 0" means the
   platform accepted the manifest, not that the new code is serving.
4. **Can we undo it?** `decide`. And where do the backups go — `backup`,
   `verify_backup`, `prune`, `backup_name`.

The plumbing is already written: `deploy/fly.toml` is the manifest and
`deploy/*.sh` are the four `flyctl` commands, gated off behind `DEPLOY_LANE=fly`
and never run against a real account by this repo. They call into this module for
every judgement, which is the split worth internalising — an untested rollback
trigger is one that fires for the first time during an incident.

Reference: ../after/src/release.py.
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

#: Tags that mean "whatever was newest when you looked".
MUTABLE_TAGS = frozenset({"latest", "main", "master", "stable", "prod", "production", "edge"})

TAG_LENGTH = 12
SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")

SECRET_VALUE_RE = re.compile(
    r"(sk-[A-Za-z0-9]{8,}|ghp_[A-Za-z0-9]{8,}|eyJ[A-Za-z0-9_-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY)"
)
SECRET_NAME_RE = re.compile(r"(SECRET|TOKEN|PASSWORD|API_KEY|PRIVATE_KEY|CREDENTIAL)", re.I)


class ReleaseError(Exception):
    """A refusal to ship. Raise it rather than returning a flag: every one of
    these is a case where continuing produces an artifact nobody can reason
    about later."""


# --- what exactly is running ----------------------------------------------------


def image_ref(registry: str, repo: str, sha: str, *, dirty: bool = False) -> str:
    """TODO 1: `registry/repo:<first TAG_LENGTH chars of sha>`.

    Raise `ReleaseError` if `sha` is not a commit SHA (`SHA_RE`) or if `dirty`.
    Refusing a dirty tree is not fussiness — the tag claims the image is that
    commit, and for uncommitted work that claim is false.
    """
    raise NotImplementedError


def is_immutable(ref: str) -> bool:
    """TODO 2: True only when the tag after the last `:` is a SHA and is not in
    MUTABLE_TAGS."""
    raise NotImplementedError


# --- where the secrets live -------------------------------------------------------


def render_manifest(
    app: str,
    image: str,
    *,
    region: str = "iad",
    secrets: Sequence[str] = (),
    env: Mapping[str, str] | None = None,
    health_path: str = "/health",
    volume: str | None = "assistant-data",
) -> dict:
    """TODO 3: the deploy manifest as data, so it can be asserted on before it is
    written.

    Refuse a mutable `image`. `secrets` is a list of NAMES — bound from the
    platform's store at boot, never rendered here. Include `force_https`, a
    health check at `health_path`, and a mount of `volume` at `/data`. Compare
    the shape you produce with `deploy/fly.toml`, which is this manifest for
    real.
    """
    raise NotImplementedError


def leaked_secrets(manifest: Mapping) -> list[str]:
    """TODO 4: env keys whose VALUE is a credential — sorted, so the failure
    message is stable.

    Two ways to fail, the same mistake in different clothes: a value that looks
    like a key (`SECRET_VALUE_RE`), or a key NAMED like one (`SECRET_NAME_RE`)
    holding anything at all. The second catches `PASSWORD = "changeme"`, which
    reaches production more often than any real key does.
    """
    raise NotImplementedError


# --- did it actually work ----------------------------------------------------------


@dataclass(frozen=True)
class Probe:
    """One post-deploy question and its answer."""

    name: str
    ok: bool
    detail: str = ""


def smoke(
    *,
    health: Mapping | None,
    expected_sha: str,
    unauthenticated_status: int | None,
    answered: bool,
) -> list[Probe]:
    """TODO 5: four probes, named `reachable`, `version`, `auth`, `answers`.

    - `reachable`: `health` is not None.
    - `version`: `health["version"]` starts with the first TAG_LENGTH chars of
      `expected_sha`. This is the one people leave out and the one that catches
      a half-finished deploy with an old machine still in the pool — a genuinely
      healthy service that passes every other check.
    - `auth`: success is a **401 or 403**. Healthy and wide open is the worst
      state on this list and the only one nothing else complains about.
    - `answers`: one real request completed.

    Put something useful in `detail` — it is what goes in the incident note, so
    say what was expected as well as what happened.
    """
    raise NotImplementedError


def passed(probes: Sequence[Probe]) -> bool:
    """TODO 6: all of them, or it did not pass."""
    raise NotImplementedError


# --- can we undo it ------------------------------------------------------------------


@dataclass(frozen=True)
class Decision:
    action: str  # "promote" | "rollback" | "halt"
    target: str = ""
    reason: str = ""
    failures: tuple[str, ...] = field(default_factory=tuple)


def decide(probes: Sequence[Probe], *, current: str, previous: str | None) -> Decision:
    """TODO 7: promote, roll back, or halt.

    `halt` is the one to think about. Rolling back is not always available, and
    a script that pretends otherwise turns a bad deploy into an outage: with no
    previous IMMUTABLE tag there is nothing to roll back to, and the honest move
    is to leave the broken release up — where it is at least visible — and page
    a human.
    """
    raise NotImplementedError


# --- state you cannot regenerate --------------------------------------------------------


def backup(db_path: str | Path, dest: str | Path) -> Path:
    """TODO 8: online backup via `sqlite3.Connection.backup`, never a file copy.

    Open the source read-only (`file:...?mode=ro`, `uri=True`), create `dest`'s
    parent, copy, close both, return `dest`. A `cp` of a database being written
    to is torn — the WAL and the main file disagree — and you find out at
    restore time, which is the worst moment on offer.
    """
    raise NotImplementedError


def verify_backup(path: str | Path, tables: Sequence[str]) -> dict[str, int]:
    """TODO 9: row counts per table, so the copy is proven readable as it is taken.

    An unverified backup is a folder of files you hope are a database. Table
    names are interpolated into SQL (they cannot be bound), so check
    `str.isidentifier()` first and raise `ReleaseError` otherwise.
    """
    raise NotImplementedError


def prune(names: Sequence[str], keep: int) -> list[str]:
    """TODO 10: which backups to delete, newest `keep` retained. Raise if
    `keep < 1`. Sorting is enough because `backup_name` starts with a timestamp
    — that is the reason to spend a thought on the naming scheme."""
    raise NotImplementedError


def backup_name(*, at: str, sha: str) -> str:
    """TODO 11: `<iso-utc, no punctuation>-<short sha>.db`, e.g.
    `20260801T221500-9f2c1ab34de5.db`. The SHA answers the question that always
    follows a restore: which code wrote this?"""
    raise NotImplementedError


# --- the CLI the deploy scripts call -------------------------------------------------


def _fetch(
    url: str, token: str | None = None, body: dict | None = None, timeout: float = 20.0
) -> tuple[int, str]:
    """Status and body, with the status KEPT on an HTTP error rather than raised —
    a 401 is the expected answer to one of the probes above, so an exception here
    would turn the passing case into the failing one."""
    import urllib.error
    import urllib.request

    payload = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(url, data=payload)
    if payload is not None:
        request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except OSError as exc:
        return 0, str(exc)


def _verify(url: str, sha: str, token: str | None) -> int:
    """`python src/release.py verify --url ... --sha ...` — exit 0 promotes.

    The shell script owns `fly deploy` and the rollback; this owns the judgement.
    Given, so that your `smoke()` is what decides.
    """
    status, body = _fetch(f"{url}/health", token)
    try:
        health = json.loads(body) if status == 200 else None
    except json.JSONDecodeError:
        health = None
    question = {"question": "what is this service"}
    # No token on purpose: this probe passes when the answer is 401.
    anonymous, _ = _fetch(f"{url}/ask", body=question)
    answered = _fetch(f"{url}/ask", token, body=question)[0] == 200
    probes = smoke(
        health=health, expected_sha=sha, unauthenticated_status=anonymous, answered=answered
    )
    for probe in probes:
        print(f"{'ok  ' if probe.ok else 'FAIL'} {probe.name}: {probe.detail}")
    return 0 if passed(probes) else 1


def main(argv: Sequence[str]) -> int:
    args = list(argv)
    pairs = [a for a in args[1:] if a != "--dirty"]
    options = dict(zip(pairs[::2], pairs[1::2], strict=False))
    try:
        if args[:1] == ["tag"]:
            registry, _, repo = options.get("--registry", "").rpartition("/")
            print(image_ref(registry, repo, options.get("--sha", ""), dirty="--dirty" in args))
            return 0
        if args[:1] == ["verify"]:
            return _verify(
                options.get("--url", os.getenv("DEPLOY_URL", "")),
                options.get("--sha", os.getenv("DEPLOY_SHA", "")),
                os.getenv("DEPLOY_SMOKE_TOKEN"),
            )
    except ReleaseError as refusal:
        # A refusal is an answer, not a crash. `set -e` in the calling script
        # stops the deploy on the exit code; a traceback would bury the one line
        # that says why.
        print(f"refusing to release: {refusal}", file=sys.stderr)
        return 1
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
