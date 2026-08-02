"""The release lane, proven offline: no registry, no cloud account, no deploy.

Every function here is the pure half of a step whose other half is one `fly`
command. That split is the whole design — the judgement (is this tag safe, did
the smoke pass, what do we roll back to) is testable, and the plumbing is three
lines of shell. An untested rollback trigger fires for the first time during an
incident, which is not when you want to discover it inverts a condition.
"""
from __future__ import annotations

import sqlite3
import threading

import pytest

from src.release import (
    Probe,
    ReleaseError,
    backup,
    backup_name,
    decide,
    image_ref,
    is_immutable,
    leaked_secrets,
    passed,
    prune,
    render_manifest,
    smoke,
    verify_backup,
)

SHA = "9f2c1ab34de5f6789012345678901234567890ab"
SHORT = SHA[:12]
IMAGE = f"registry.fly.io/assistant:{SHORT}"


def ok_probes() -> list[Probe]:
    return smoke(
        health={"version": SHORT, "status": "ok"},
        expected_sha=SHA,
        unauthenticated_status=401,
        answered=True,
    )


# --- what exactly is running ----------------------------------------------------


def test_the_published_tag_is_the_commit_sha():
    assert image_ref("registry.fly.io", "assistant", SHA) == IMAGE


def test_a_dirty_tree_cannot_be_tagged_with_a_commit():
    """The tag claims the image is that commit. For a dirty tree that claim is
    false, and the only way to find out what shipped is to ask someone who has
    since left the company."""
    with pytest.raises(ReleaseError, match="dirty"):
        image_ref("registry.fly.io", "assistant", SHA, dirty=True)


def test_a_version_string_is_not_a_commit():
    """`v1.4.2` is a name someone chose and can choose again."""
    with pytest.raises(ReleaseError, match="not a commit sha"):
        image_ref("registry.fly.io", "assistant", "v1.4.2")


@pytest.mark.parametrize("tag", ["latest", "main", "production", "stable"])
def test_a_moving_tag_is_not_immutable(tag):
    """This is the rollback that silently does nothing: you redeploy `latest` and
    get the code you were rolling back FROM, because the tag moved with you."""
    assert not is_immutable(f"registry.fly.io/assistant:{tag}")


def test_a_sha_tag_is_immutable():
    assert is_immutable(IMAGE)


# --- where the secrets live -------------------------------------------------------


def test_the_manifest_names_its_secrets_and_holds_none_of_them():
    manifest = render_manifest(
        "assistant", IMAGE, secrets=["JWT_SIGNING_KEY", "TELEGRAM_BOT_TOKEN"]
    )
    assert manifest["secrets"] == ["JWT_SIGNING_KEY", "TELEGRAM_BOT_TOKEN"]
    assert leaked_secrets(manifest) == []


def test_a_manifest_carrying_a_mutable_tag_is_refused():
    with pytest.raises(ReleaseError, match="mutable tag"):
        render_manifest("assistant", "registry.fly.io/assistant:latest")


def test_a_key_pasted_into_the_manifest_is_caught_before_it_reaches_git():
    """A manifest is a file in history. Once the value is in it, rotating the key
    is the only remedy and `git filter-branch` is the cleanup."""
    manifest = render_manifest("assistant", IMAGE, env={"OPENAI_API_KEY": "sk-abcd1234efgh"})
    assert leaked_secrets(manifest) == ["OPENAI_API_KEY"]


def test_a_placeholder_password_counts_as_a_leak():
    """`changeme` looks like nothing and is the value that reaches production more
    often than any real key does. The NAME is enough to refuse."""
    manifest = render_manifest("assistant", IMAGE, env={"DB_PASSWORD": "changeme"})
    assert leaked_secrets(manifest) == ["DB_PASSWORD"]


def test_ordinary_configuration_is_not_a_leak():
    manifest = render_manifest(
        "assistant", IMAGE, env={"ASSISTANT_TIER": "local", "REQUEST_DEADLINE_SECONDS": "30"}
    )
    assert leaked_secrets(manifest) == []


def test_the_manifest_forces_https_and_mounts_the_one_stateful_volume():
    manifest = render_manifest("assistant", IMAGE)
    assert manifest["http_service"]["force_https"] is True
    assert manifest["mounts"][0]["destination"] == "/data"


# --- did it actually work ----------------------------------------------------------


def test_a_healthy_service_running_the_wrong_code_fails_the_smoke():
    """The failure nobody checks for: the deploy half-succeeded and an old machine
    is still in the pool. It is genuinely healthy, it answers correctly, and every
    other probe passes against it — because it is a working service, just not the
    one you shipped."""
    probes = smoke(
        health={"version": "0000deadbeef"},
        expected_sha=SHA,
        unauthenticated_status=401,
        answered=True,
    )
    assert not passed(probes)
    assert [p.name for p in probes if not p.ok] == ["version"]


def test_a_200_for_an_anonymous_caller_fails_the_smoke():
    """Success for this probe is a 401. Healthy and wide open is the worst state
    on the list and the only one nothing else in the system complains about."""
    probes = smoke(
        health={"version": SHORT}, expected_sha=SHA, unauthenticated_status=200, answered=True
    )
    assert [p.name for p in probes if not p.ok] == ["auth"]


def test_an_unreachable_service_fails_rather_than_erroring():
    probes = smoke(
        health=None, expected_sha=SHA, unauthenticated_status=None, answered=False
    )
    assert [p.name for p in probes if not p.ok] == ["reachable", "version", "auth", "answers"]


def test_all_four_green_is_the_only_way_to_pass():
    assert passed(ok_probes())


# --- can we undo it ------------------------------------------------------------------


def test_a_clean_smoke_promotes():
    assert decide(ok_probes(), current=IMAGE, previous=None).action == "promote"


def test_a_failed_smoke_rolls_back_to_the_previous_immutable_tag():
    previous = "registry.fly.io/assistant:0000deadbeef"
    decision = decide(
        smoke(health=None, expected_sha=SHA, unauthenticated_status=None, answered=False),
        current=IMAGE,
        previous=previous,
    )
    assert decision.action == "rollback"
    assert decision.target == previous
    assert "reachable" in decision.failures


def test_there_is_no_rolling_back_to_latest():
    """Rolling back to a moving tag is the appearance of a fix. Halting is worse
    for the graph and better for the incident: the broken release stays visible
    and a human gets paged instead of a script pretending it recovered."""
    decision = decide(
        smoke(health=None, expected_sha=SHA, unauthenticated_status=None, answered=False),
        current=IMAGE,
        previous="registry.fly.io/assistant:latest",
    )
    assert decision.action == "halt"


def test_a_first_deploy_with_nothing_behind_it_halts_rather_than_lying():
    decision = decide(
        smoke(health=None, expected_sha=SHA, unauthenticated_status=None, answered=False),
        current=IMAGE,
        previous=None,
    )
    assert decision.action == "halt" and "no immutable previous release" in decision.reason


# --- state you cannot regenerate --------------------------------------------------------


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "assistant.db"
    connection = sqlite3.connect(path)
    connection.execute("create table audit_log (id integer primary key, what text)")
    connection.executemany("insert into audit_log (what) values (?)", [("a",), ("b",), ("c",)])
    connection.commit()
    return path, connection


def test_a_backup_taken_mid_write_is_still_a_valid_database(db, tmp_path):
    """The reason this is not `cp`. A file copy of a database being written to is
    torn — the WAL and the main file disagree — and you find that out at restore
    time, which is the worst moment available."""
    path, connection = db
    writing = threading.Event()

    def churn():
        writer = sqlite3.connect(path)
        for i in range(200):
            writer.execute("insert into audit_log (what) values (?)", (f"row{i}",))
            writer.commit()
            writing.set()
        writer.close()

    thread = threading.Thread(target=churn)
    thread.start()
    writing.wait(timeout=5)
    copy = backup(path, tmp_path / "backups" / "mid-write.db")
    thread.join()
    connection.close()
    assert verify_backup(copy, ["audit_log"])["audit_log"] >= 3


def test_a_backup_is_verified_at_the_moment_it_is_taken(db, tmp_path):
    """An unverified backup is a folder of files you hope are a database. The
    check is one query and it runs in the same script as the copy, which is the
    only place it will ever actually get run."""
    path, connection = db
    connection.close()
    counts = verify_backup(backup(path, tmp_path / "b.db"), ["audit_log"])
    assert counts == {"audit_log": 3}


def test_verifying_an_unreadable_backup_raises_instead_of_reporting_success(tmp_path):
    junk = tmp_path / "not-a-db.db"
    junk.write_bytes(b"this is not a sqlite file")
    with pytest.raises(sqlite3.DatabaseError):
        verify_backup(junk, ["audit_log"])


def test_the_backup_name_sorts_chronologically_and_names_the_code_that_wrote_it():
    name = backup_name(at="2026-08-01T22:15:00", sha=SHA)
    assert name == f"20260801T221500-{SHORT}.db"
    assert sorted([backup_name(at="2026-08-02T00:00:00", sha=SHA), name])[0] == name


def test_retention_keeps_the_newest_and_names_the_rest_for_deletion():
    names = [backup_name(at=f"2026-08-0{d}T00:00:00", sha=SHA) for d in range(1, 6)]
    doomed = prune(names, keep=2)
    assert doomed == names[:3], "sorted by name because the name starts with the timestamp"


def test_retention_that_keeps_nothing_is_a_bug_not_a_policy():
    with pytest.raises(ReleaseError):
        prune(["a.db"], keep=0)
