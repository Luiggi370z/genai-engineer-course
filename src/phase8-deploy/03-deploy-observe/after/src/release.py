"""The release lane: publish, deploy, prove, and undo — on Fly.io, as one worked example.

`observe.py` answers "is it healthy?". This answers the four questions that come
before and after that one, and each exists because of a specific way a deploy goes
wrong at 2am.

**What exactly is running?** An image tagged `latest` is a *name*, not a version.
Roll back to `latest` and you get the code you just rolled back FROM, because the
tag moved. So the only tag this module will publish is the commit SHA, and it
refuses a dirty tree — an image built from uncommitted work is an image no commit
can reproduce.

**Where do the secrets live?** In the platform's secret store, bound at boot by
NAME. A manifest is a file in git; the moment a key's value is in it, the key is
in the history forever and rotating it is a git filter-branch. `leaked_secrets`
is a gate, not advice.

**Did it actually work?** "The deploy command exited 0" means the platform
accepted the manifest. Smoke checks mean the new code is serving: `/health` must
report the SHA we just shipped (otherwise an old machine is still answering and
every check passes against the previous release), one real request must succeed,
and an unauthenticated request must be REFUSED — a service that is healthy and
wide open is the worst outcome of the four, and the one a health check will
never catch.

**Can we undo it?** Only to a previous immutable tag, and only if we have one.
`decide()` returns the rollback target as data, so the script does not have to
guess it while the pager is going off.

## Not live-provisioned

Everything here is executable and nothing here has been run against a paid
account by this repo. `deploy/*.sh` refuse to do anything unless `DEPLOY_LANE=fly`
and the app's env vars are set, which is the same gating the OAuth and
guard-model lanes use: a reference you can run, off by default.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

#: Tags that mean "whatever was newest when you looked". Every one of these is a
#: rollback that silently does nothing.
MUTABLE_TAGS = frozenset({"latest", "main", "master", "stable", "prod", "production", "edge"})

#: A commit SHA is 40 hex chars; 12 is the conventional short form and still
#: collision-free for any repo a person will work on.
TAG_LENGTH = 12
SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")

#: Values that look like credentials rather than configuration. Deliberately
#: crude — the point is to catch the copy-paste, not to be a scanner.
SECRET_VALUE_RE = re.compile(
    r"(sk-[A-Za-z0-9]{8,}|ghp_[A-Za-z0-9]{8,}|eyJ[A-Za-z0-9_-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY)"
)
#: Names that should never appear as a literal value, whatever the value looks like.
SECRET_NAME_RE = re.compile(r"(SECRET|TOKEN|PASSWORD|API_KEY|PRIVATE_KEY|CREDENTIAL)", re.I)


class ReleaseError(Exception):
    """A refusal to ship. Raised, not returned: every one of these is a case where
    continuing produces an artifact nobody can reason about later."""


# --- what exactly is running ----------------------------------------------------


def image_ref(registry: str, repo: str, sha: str, *, dirty: bool = False) -> str:
    """`registry/repo:<short-sha>` — the only tag shape this lane publishes.

    `dirty` comes from `git status --porcelain` being non-empty. Refusing it is
    not fussiness: the tag claims the image is that commit, and for a dirty tree
    that claim is false. Six months later the only way to find out what shipped
    is to ask someone who has left.
    """
    sha = sha.strip().lower()
    if not SHA_RE.match(sha):
        raise ReleaseError(f"not a commit sha: {sha!r} — tag from git, not from a version string")
    if dirty:
        raise ReleaseError("working tree is dirty; commit first so the tag means something")
    return f"{registry}/{repo}:{sha[:TAG_LENGTH]}"


def is_immutable(ref: str) -> bool:
    """True when the tag can only ever point at one image."""
    tag = ref.rpartition(":")[2]
    return bool(tag) and tag.lower() not in MUTABLE_TAGS and bool(SHA_RE.match(tag))


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
    """The deploy manifest as data, so it can be asserted on before it is written.

    `secrets` is a list of NAMES. They are bound from the platform's store at boot
    (`fly secrets set`), never rendered here, and the manifest records only that
    the app requires them — which is exactly the audit question ("what does this
    service need access to?") answered by a file you can read.

    TLS is not a field because on Fly it is not a decision: the platform
    terminates it and `force_https` redirects the rest. On a VM this is where a
    Caddy block would go, and the same principle applies — no plaintext listener,
    ever, once an auth token is crossing the wire.
    """
    if not is_immutable(image):
        raise ReleaseError(f"refusing to deploy a mutable tag: {image}")
    return {
        "app": app,
        "primary_region": region,
        "build": {"image": image},
        "env": dict(env or {}),
        "secrets": list(secrets),
        "http_service": {
            "internal_port": 8000,
            "force_https": True,
            "auto_stop_machines": False,
            "checks": [{"type": "http", "path": health_path, "interval": "15s"}],
        },
        "mounts": ([{"source": volume, "destination": "/data"}] if volume else []),
    }


def leaked_secrets(manifest: Mapping) -> list[str]:
    """Env keys whose VALUE is a credential. A non-empty list blocks the deploy.

    Two ways to fail this, and both are the same mistake in different clothes: a
    value that looks like a key (`sk-...`), or a key named like one holding
    anything at all. The second catches `PASSWORD = "changeme"`, which is the
    placeholder that reaches production more often than any real key does.
    """
    found = []
    for key, value in (manifest.get("env") or {}).items():
        text = str(value)
        if SECRET_VALUE_RE.search(text) or (SECRET_NAME_RE.search(key) and text):
            found.append(key)
    return sorted(found)


# --- did it actually work ----------------------------------------------------------


@dataclass(frozen=True)
class Probe:
    """One post-deploy question and its answer. `detail` is what goes in the
    incident note, so it says what was expected as well as what happened."""

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
    """Four probes, in the order they stop being worth running.

    The version probe is the one people leave out and the one that catches the
    nastiest failure: a deploy that half-succeeded, with an old machine still in
    the pool. Every other check passes against it — it IS a healthy service, just
    the wrong one.

    The auth probe inverts the usual polarity: success is a **401**. A green
    health check on a service that answers anonymous requests is the worst
    combination on this list, because nothing else in the system will complain.
    """
    running = str((health or {}).get("version") or "")
    want = expected_sha[:TAG_LENGTH]
    return [
        Probe("reachable", health is not None, "GET /health returned a body"),
        Probe(
            "version",
            running.startswith(want),
            f"serving {running or '<none>'}, deployed {want}",
        ),
        Probe(
            "auth",
            unauthenticated_status in (401, 403),
            f"anonymous request got {unauthenticated_status}, want 401/403",
        ),
        Probe("answers", answered, "one real request completed end to end"),
    ]


def passed(probes: Sequence[Probe]) -> bool:
    return all(p.ok for p in probes)


# --- can we undo it ------------------------------------------------------------------


@dataclass(frozen=True)
class Decision:
    action: str  # "promote" | "rollback" | "halt"
    target: str = ""
    reason: str = ""
    failures: tuple[str, ...] = field(default_factory=tuple)


def decide(probes: Sequence[Probe], *, current: str, previous: str | None) -> Decision:
    """Promote, roll back, or stop and get a human.

    `halt` exists because "roll back" is not always available, and pretending
    otherwise is how a script turns a bad deploy into an outage. With no previous
    immutable tag there is nothing to roll back TO — the honest move is to leave
    the broken release up, where it is at least visible, and page someone.
    """
    failures = tuple(p.name for p in probes if not p.ok)
    if not failures:
        return Decision("promote", current, "all smoke checks passed")
    if previous and is_immutable(previous):
        return Decision("rollback", previous, f"smoke failed: {', '.join(failures)}", failures)
    return Decision(
        "halt", "", f"smoke failed ({', '.join(failures)}) and no immutable previous release",
        failures,
    )


# --- state you cannot regenerate --------------------------------------------------------


def backup(db_path: str | Path, dest: str | Path) -> Path:
    """Online backup via SQLite's own API, never `cp`.

    A file copy of a database being written to is a torn copy: SQLite is
    mid-transaction, the WAL and the main file disagree, and you find out at
    restore time, which is the worst possible time. `Connection.backup` copies
    pages under the database's own lock and produces a file that is a valid
    database at a consistent point in time.
    """
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    target = sqlite3.connect(dest)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()
    return dest


def verify_backup(path: str | Path, tables: Sequence[str]) -> dict[str, int]:
    """Row counts per table, so a backup is proven readable at the moment it is taken.

    An unverified backup is a folder of files you *hope* are a database. This is
    the cheapest possible proof and it runs in the same script as the copy —
    which is the only place it will actually get run.
    """
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        counts = {}
        for table in tables:
            if not table.isidentifier():
                raise ReleaseError(f"not a table name: {table!r}")
            counts[table] = connection.execute(f"select count(*) from {table}").fetchone()[0]
        return counts
    finally:
        connection.close()


def prune(names: Sequence[str], keep: int) -> list[str]:
    """Which backups to delete, newest `keep` retained.

    Names sort chronologically because `backup_name` puts an ISO timestamp first
    — the reason to spend a thought on the naming scheme is so that retention is
    a sort and not a stat() of every file.
    """
    if keep < 1:
        raise ReleaseError("keep at least one backup")
    return sorted(names)[: max(0, len(names) - keep)]


def backup_name(*, at: str, sha: str) -> str:
    """`<iso-utc>-<short-sha>.db`. The SHA is there so a restore can answer the
    question that always follows a restore: which code wrote this?"""
    stamp = at.replace(":", "").replace("-", "")
    return f"{stamp}-{sha[:TAG_LENGTH]}.db"


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

    The shell script owns `fly deploy` and `fly releases rollback`; this owns the
    judgement. Keeping the decision in Python is what makes it testable, and an
    untested rollback trigger is one that fires for the first time during an
    incident.
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
    """Two subcommands, both called by `deploy/release.sh`.

    Argument parsing is eight lines rather than an argparse tree on purpose: this
    is a seam between a shell script and tested logic, and the interesting part
    is on the other side of it.
    """
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
        # stops the deploy on the exit code; a traceback would just bury the one
        # line that says why.
        print(f"refusing to release: {refusal}", file=sys.stderr)
        return 1
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
