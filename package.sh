#!/usr/bin/env bash
# Builds the two things a student receives.
#
#   dist/course.html                       the workbook, one self-contained file
#   dist/genai-engineer-workbook-src.zip   the companion repo, source only
#
# The zip is cut from HEAD; the workbook is built from the working tree.
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
set -euo pipefail

cd "$(dirname "$0")"

NAME="genai-engineer-workbook-src"
OUT="dist"

# `pnpm ship` writes dist/course.html itself, so the loose deliverable is a build
# output rather than a file committed under src/ — the zip is source only.
echo "==> Building the workbook"
(cd app && pnpm ship)

# `git archive` reads HEAD, not the working tree, so a lesson with uncommitted
# edits would quietly ship its old version — stop and say which.
#
# The refresh is load-bearing: `diff-index` trusts the index's cached stat data,
# and running the lessons rewrites tracked files (ruff --fix, formatters) with
# identical content. That still moves the mtime, which would otherwise report as a
# change and train whoever sees it to ignore the check.
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
