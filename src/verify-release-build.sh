#!/usr/bin/env bash
# Builds the capstone image the way a student receives it: from a clean `git archive`
# extract, not the working tree.
#
#   ./src/verify-release-build.sh
#
# This exists because the working tree lies. Running the lessons leaves an ignored
# uv.lock behind, so `docker compose build` succeeds locally while the shipped ZIP —
# and every clean CI checkout — fails at `COPY pyproject.toml uv.lock`. The only
# honest test of a release artifact is to build the release artifact.
#
# Two checks, cheapest first:
#   1. every file the capstone Dockerfile COPYs is tracked in git;
#   2. the extracted archive actually builds.
#
# Pass --files-only to skip the Docker build (no daemon in some CI lanes).
set -euo pipefail

cd "$(dirname "$0")/.."
CAPSTONE="src/workshops/assistant/after"
FILES_ONLY=${1:-}

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

echo "==> Extracting src/ from HEAD"
git archive --format=tar HEAD -- src | tar -x -C "$work"

echo "==> Checking the image's build inputs survived the archive"
missing=0
# Parse the COPY lines rather than hardcoding a list: a Dockerfile edit that adds a
# build input should fail here, not in a student's terminal three weeks later.
# `COPY --from=` moves files between build stages, so it has no repo file behind it.
while read -r src_path; do
  if [ ! -e "$work/$CAPSTONE/$src_path" ]; then
    echo "error: $CAPSTONE/$src_path is COPYd by the Dockerfile but is not in HEAD" >&2
    echo "       (ignored by .gitignore? it needs a negation rule)" >&2
    missing=1
  fi
done < <(awk '/^COPY / && !/--from=/ {for (i = 2; i < NF; i++) print $i}' "$CAPSTONE/Dockerfile")
[ "$missing" -eq 0 ] || exit 1
echo "    all Dockerfile inputs are tracked"

if [ "$FILES_ONLY" = "--files-only" ]; then
  echo
  echo "  release build inputs OK (skipped the image build)"
  exit 0
fi

echo "==> Building the capstone image from the extract"
docker build -t genai-capstone:release-check "$work/$CAPSTONE"

echo
echo "  the shipped source builds a capstone image"
