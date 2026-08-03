#!/usr/bin/env bash
# Builds the three things a student receives, plus the stamp that proves where
# they came from.
#
#   dist/README.md                         how to start, from release/README.md
#   dist/course.html                       the workbook, one self-contained file
#   dist/genai-engineer-workbook-src.zip   the companion repo, source only
#   dist/BUILD.json                        the commit, the trees, the hashes
#
# **Everything comes from one commit.** The zip is `git archive HEAD`; the
# workbook is built from the working tree, so the tree has to match HEAD for the
# two to be the same release. Earlier this was only checked for `src/`, which let
# a `dist/course.html` built from uncommitted app edits ship beside a zip cut
# from HEAD — two different releases in one folder, and nothing said so.
#
# **Nothing lands until all of it is ready.** The build happens in a scratch
# directory and replaces `dist/` in one move at the end. The old version failed
# the HEAD check *after* `pnpm ship` had already overwritten `dist/course.html`,
# so an aborted package left a new workbook next to the previous zip — the exact
# mismatch the check exists to prevent, created by the check.
#
# The zip comes from `git archive` rather than `zip -x` and a list of exclusions:
# the working tree carries several gigabytes of .venv and __pycache__ from running
# the lessons, and a hand-maintained exclude list is exactly the kind of thing that
# is right the day it is written and wrong three lessons later. Tracked files only
# makes .gitignore the single source of truth for what ships.
#
# That also drops each lesson's uv.lock, which this repo classifies as a build
# artifact. Deliberate: the upper-bounded pins in every pyproject.toml are what the
# course actually teaches about reproducibility, and a lock file resolved on one
# machine in 2026 is not a gift to whoever installs later.
#
# One exception, tracked in .gitignore: workshops/assistant/after/uv.lock. A lesson
# is installed with `uv sync`, which resolves; the capstone image is built with
# `uv sync --frozen`, which does not. That lock is a build input, and a release that
# omits it produces a ZIP nobody can `docker compose build`. verify-release-build.sh
# proves the shipped archive still builds.
set -euo pipefail

cd "$(dirname "$0")"

NAME="genai-engineer-workbook-src"
OUT="dist"
STAGE="$OUT.staging"

rm -rf "$STAGE"
trap 'rm -rf "$STAGE"' EXIT

# `git archive` reads HEAD, not the working tree, so a directory with uncommitted
# edits would quietly ship its old version — stop and say which.
#
# All three inputs, not just `src`: `app/` is where the workbook is built from and
# `release/README.md` is shipped verbatim, so an edit to either makes `dist/` a
# mixture of two commits.
#
# The refresh is load-bearing: `diff-index` trusts the index's cached stat data,
# and running the lessons rewrites tracked files (ruff --fix, formatters) with
# identical content. That still moves the mtime, which would otherwise report as a
# change and train whoever sees it to ignore the check.
git update-index -q --refresh
if ! git diff-index --quiet HEAD -- src app release; then
  echo >&2
  echo "error: src/, app/ or release/ differs from HEAD, and a release is one commit." >&2
  echo "       Commit these first, or dist/ will mix a working-tree workbook with" >&2
  echo "       a zip cut from HEAD:" >&2
  git status --short -- src app release >&2
  exit 1
fi

echo "==> Building the workbook"
mkdir -p "$STAGE"
# `pnpm ship` writes into app/dist and then copies; point it at the staging dir so
# a failed run cannot touch the released one.
(cd app && pnpm build)
cp app/dist/course.html "$STAGE/course.html"
cp release/README.md "$STAGE/README.md"

echo "==> Packaging the companion repo"
# One generated member rides along: src/RELEASE_COMMIT. `verify-e2e.sh` bakes the
# commit into the image so /health can say which code is serving, and it read that
# from git — which the archive does not contain. Without the stamp the shipped
# verifier compared the image's `dev` version against an empty string and failed
# check 3 on a stack that was fine.
#
# The prefix dance is `git archive`'s rule, not ours: `--add-file` takes the last
# `--prefix` seen BEFORE it, so the src-level prefix is set for the stamp and then
# reset for the tracked tree.
commit=$(git rev-parse HEAD)
printf '%s\n' "$commit" >"$STAGE/RELEASE_COMMIT"
git archive --format=zip \
  --prefix="$NAME/src/" --add-file="$STAGE/RELEASE_COMMIT" \
  --prefix="$NAME/" \
  -o "$STAGE/$NAME.zip" HEAD -- src
rm -f "$STAGE/RELEASE_COMMIT"

# Belt and braces. If the ignore rules ever stop covering a build artifact, the
# failure should be loud here rather than a multi-gigabyte download for a student.
if unzip -l "$STAGE/$NAME.zip" | grep -Eq '(\.venv/|__pycache__/|\.pyc$|\.pytest_cache/|\.ruff_cache/)'; then
  echo "error: build artifacts reached the zip — check .gitignore" >&2
  exit 1
fi

# The other direction, which is the one that actually went wrong: documents
# falling *out*. A bare `docs/` in .gitignore matched three directories instead of
# one, so the capstone's release checklist was never tracked and never packaged
# while seven places in `src/` told the student to read it. `check-doc-links`
# (inside `pnpm build`, above) fails on the reference; this counts the files,
# because a `.gitattributes` export-ignore would drop a *tracked* document from
# the archive and leave every reference to it looking fine.
want=$(git ls-files -- src | grep -c '\.md$' || true)
got=$(unzip -l "$STAGE/$NAME.zip" | grep -c '\.md$' || true)
if [ "$want" -ne "$got" ]; then
  echo "error: $want tracked document(s) under src/, but $got reached the zip." >&2
  echo "       git archive dropped something — check .gitattributes for export-ignore." >&2
  exit 1
fi

# The stamp. It travels with the release so whoever holds these three files can
# say which commit produced them, and `verify-dist.sh` reads it to answer "is the
# dist/ in this working directory still the release of the commit I am on" before
# somebody uploads one built a dozen commits ago — a question no amount of looking
# at the files themselves can settle, because a minified bundle looks equally
# plausible whatever it was built from.
echo "==> Stamping the build"
python3 - "$STAGE" "$commit" "$NAME" <<'PY'
import datetime as dt, hashlib, json, re, subprocess, sys, zipfile
from pathlib import Path

stage, commit, name = Path(sys.argv[1]), sys.argv[2], sys.argv[3]

#: Bumped when a consumer would have to change to read this file correctly —
#: a key renamed or removed, or a value's meaning altered. Adding a key is not a
#: bump: `verify-dist.sh` and `release.yml` both read keys by name, so a new one is
#: inert until something asks for it. The point of declaring it is that a *future*
#: reader can refuse a stamp it does not understand instead of silently reading
#: `trees` out of a file where that word came to mean something else.
SCHEMA_VERSION = 1

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def tree(prefix):
    return subprocess.run(
        ["git", "rev-parse", f"HEAD:{prefix}"], capture_output=True, text=True, check=True
    ).stdout.strip()

def run(*args):
    """First line of a tool's own version output, or "absent"."""
    try:
        done = subprocess.run(args, capture_output=True, text=True, check=False)
    except OSError:
        return "absent"
    if done.returncode != 0:
        return "absent"
    return done.stdout.strip().splitlines()[0] if done.stdout.strip() else "absent"

def tool_version(*args):
    """Just the number. Every one of these prints it differently — `v24.15.0`,
    `Python 3.12.11`, `git version 2.54.0`, and uv appends its build platform — and
    a field called `node` reading `v24.15.0` invites a string comparison against
    `24.15.0` that quietly never matches."""
    raw = run(*args)
    if raw == "absent":
        return raw
    found = re.search(r"\d+(?:\.\d+)+", raw)
    return found.group(0) if found else raw

def version():
    """The release's number, and where it came from.

    The tag wins. `app/package.json` carries a version too, and nothing reconciled
    the two — the workflow triggers on `v*` tags while that file said `1.0.0`
    regardless, so "which version is this" had two answers and no tie-break. At
    release time the tag is the answer, because it is the thing a person typed on
    purpose and the thing the release is named after. Off a tag there is no tag to
    read, so `package.json` stands in and says so.
    """
    tag = run("git", "describe", "--exact-match", "--tags", "HEAD")
    if tag != "absent":
        return tag, "git-tag"
    declared = json.loads(Path("app/package.json").read_text())["version"]
    return declared, "app/package.json"

course_version, version_source = version()

# One digest per member, of the member's CONTENT rather than of the archive.
# The archive's own hash is already in `artifacts`, and it answers a narrower
# question than it appears to: rezipping the same files with a different git or
# compression level changes it, so a mismatch there means "rebuilt", not
# "different". Hashing what is inside each entry is stable across all of that,
# which is what lets verify-dist.sh compare the shipped tree against HEAD file by
# file instead of comparing a list of names and hoping the bytes followed.
with zipfile.ZipFile(stage / f"{name}.zip") as zf:
    members = {
        info.filename.removeprefix(f"{name}/"): hashlib.sha256(zf.read(info)).hexdigest()
        for info in zf.infolist()
        if not info.is_dir()
    }

stamp = {
    "schema_version": SCHEMA_VERSION,
    "version": course_version,
    "version_source": version_source,
    # UTC with an explicit `Z`, because a release stamp read six months later on
    # another continent should not need the reader to guess an offset.
    "built_at": dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    # What built it, not what it needs. A course.html that only reproduces under
    # one bundler version is a fact worth recording rather than discovering: the
    # tree hashes below can match while the artifact differs, and this is the
    # first thing to compare when they do. `uv` is here even though it builds
    # nothing in `dist/` — it is the toolchain the shipped lessons are run with,
    # and "absent" is a truthful answer on a machine that packaged without it.
    "toolchain": {
        "node": tool_version("node", "--version"),
        "pnpm": tool_version("pnpm", "--version"),
        "python": tool_version("python3", "--version"),
        "uv": tool_version("uv", "--version"),
        "git": tool_version("git", "--version"),
    },
    "commit": commit,
    # Tree hashes, not just the commit: they answer "did the content change"
    # rather than "was there a commit", so a docs-only commit does not make a
    # perfectly good dist/ read as stale.
    "trees": {prefix: tree(prefix) for prefix in ("src", "app", "release")},
    "artifacts": {
        "course.html": sha256(stage / "course.html"),
        "README.md": sha256(stage / "README.md"),
        f"{name}.zip": sha256(stage / f"{name}.zip"),
    },
    "files": dict(sorted(members.items())),
}
(stage / "BUILD.json").write_text(json.dumps(stamp, indent=2) + "\n")
PY

# One move, at the end. Until this line runs, dist/ is the previous release in
# full; after it, the new one in full. There is no state in between where a
# student could pull a workbook and a zip from different commits.
echo "==> Publishing"
rm -rf "$OUT.previous"
[ -d "$OUT" ] && mv "$OUT" "$OUT.previous"
mv "$STAGE" "$OUT"
rm -rf "$OUT.previous"

lessons=$(unzip -l "$OUT/$NAME.zip" | grep -c 'pyproject\.toml$' || true)
echo
echo "  $OUT/README.md           $(du -h "$OUT/README.md" | cut -f1)"
echo "  $OUT/course.html         $(du -h "$OUT/course.html" | cut -f1)"
echo "  $OUT/$NAME.zip  $(du -h "$OUT/$NAME.zip" | cut -f1)"
read -r stamp_version stamp_source members < <(python3 -c '
import json, sys
s = json.load(open(sys.argv[1]))
print(s["version"], s["version_source"], len(s["files"]))
' "$OUT/BUILD.json")
echo "  $OUT/BUILD.json          ${commit:0:12} · $members members hashed"
echo "  version $stamp_version (from $stamp_source)"
echo "  $((lessons / 2)) lesson pairs · no build artifacts"
