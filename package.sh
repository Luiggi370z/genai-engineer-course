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
git archive --format=zip --prefix="$NAME/" -o "$STAGE/$NAME.zip" HEAD -- src

# Belt and braces. If the ignore rules ever stop covering a build artifact, the
# failure should be loud here rather than a multi-gigabyte download for a student.
if unzip -l "$STAGE/$NAME.zip" | grep -Eq '(\.venv/|__pycache__/|\.pyc$|\.pytest_cache/|\.ruff_cache/)'; then
  echo "error: build artifacts reached the zip — check .gitignore" >&2
  exit 1
fi

# The stamp. `verify-dist.sh` reads this to answer "is what is committed under
# dist/ actually this commit's release, or a stale one nobody noticed" — a
# question no amount of looking at the files themselves can settle, because a
# minified bundle looks equally plausible whatever it was built from.
echo "==> Stamping the build"
commit=$(git rev-parse HEAD)
python3 - "$STAGE" "$commit" "$NAME" <<'PY'
import hashlib, json, subprocess, sys
from pathlib import Path

stage, commit, name = Path(sys.argv[1]), sys.argv[2], sys.argv[3]

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def tree(prefix):
    return subprocess.run(
        ["git", "rev-parse", f"HEAD:{prefix}"], capture_output=True, text=True, check=True
    ).stdout.strip()

stamp = {
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
echo "  $OUT/BUILD.json          ${commit:0:12}"
echo "  $((lessons / 2)) lesson pairs · no build artifacts"
