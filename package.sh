#!/usr/bin/env bash
# Builds the two things a student receives.
#
#   dist/course.html                       the workbook, one self-contained file
#   dist/genai-engineer-workbook-src.zip   the companion repo, source only
#
# Both are cut from the same commit. The zip comes from `git archive` rather than
# `zip -x` and a list of exclusions: the working tree carries several gigabytes of
# .venv and __pycache__ from running the lessons, and a hand-maintained exclude
# list is exactly the kind of thing that is right the day it is written and wrong
# three lessons later. Tracked files only makes .gitignore the single source of
# truth for what ships.
#
# That also drops each lesson's uv.lock, which this repo classifies as a build
# artifact. Deliberate: the upper-bounded pins in every pyproject.toml are what the
# course actually teaches about reproducibility, and a lock file resolved on one
# machine in 2026 is not a gift to whoever installs later.
set -euo pipefail

cd "$(dirname "$0")"

NAME="genai-engineer-workbook-src"
OUT="dist"

# Build first, into src/course.html, so the loose deliverable and the copy inside
# the zip cannot come from different builds.
echo "==> Building the workbook"
(cd app && pnpm ship)

# `git archive` reads HEAD, not the working tree. If the build just changed the
# bundle, or a lesson has uncommitted edits, the zip would quietly ship the old
# version — so stop and say which.
#
# The refresh is load-bearing: `diff-index` trusts the index's cached stat data,
# and the build above rewrites course.html every run. A byte-identical rebuild
# still moves the mtime, which would otherwise report as a change on every run and
# train whoever sees it to ignore the check.
git update-index -q --refresh
if ! git diff-index --quiet HEAD -- src; then
  echo >&2
  echo "error: src/ differs from HEAD, and git archive packages HEAD." >&2
  echo "       Commit these first or the zip will not contain them:" >&2
  git status --short -- src >&2
  exit 1
fi

echo "==> Packaging the companion repo"
mkdir -p "$OUT"
cp src/course.html "$OUT/course.html"
git archive --format=zip --prefix="$NAME/" -o "$OUT/$NAME.zip" HEAD -- src

# Belt and braces. If the ignore rules ever stop covering a build artifact, the
# failure should be loud here rather than a multi-gigabyte download for a student.
if unzip -l "$OUT/$NAME.zip" | grep -Eq '(\.venv/|__pycache__/|\.pyc$|\.pytest_cache/|\.ruff_cache/)'; then
  echo "error: build artifacts reached the zip — check .gitignore" >&2
  exit 1
fi

lessons=$(unzip -l "$OUT/$NAME.zip" | grep -c 'pyproject\.toml$' || true)
echo
echo "  $OUT/course.html         $(du -h "$OUT/course.html" | cut -f1)"
echo "  $OUT/$NAME.zip  $(du -h "$OUT/$NAME.zip" | cut -f1)"
echo "  $((lessons / 2)) lesson pairs · no build artifacts"
