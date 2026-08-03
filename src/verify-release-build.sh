#!/usr/bin/env bash
# Builds the capstone image the way a student receives it: from a clean extract,
# not the working tree.
#
#   ./src/verify-release-build.sh
#
# This exists because the working tree lies. Running the lessons leaves an ignored
# uv.lock behind, so `docker compose build` succeeds locally while the shipped ZIP —
# and every clean CI checkout — fails at `COPY pyproject.toml uv.lock`. The only
# honest test of a release artifact is to build the release artifact.
#
# Two checks, cheapest first:
#   1. every file the capstone Dockerfile COPYs is present in the extract;
#   2. the extract actually builds.
#
# Two lanes, because this script is itself shipped inside the companion ZIP and a
# student who unpacked it has no `.git` to archive:
#
#   git    a checkout: extract from HEAD, so "present" means "tracked". This is
#          the lane that catches the working-tree lie, and the one CI runs.
#   tree   an unpacked release: the tree already *is* a clean extract, so there is
#          nothing to extract it from. Same two checks, one weaker — see the
#          warning it prints. It ran `git archive` blind before this, and told a
#          student holding a perfectly good release "fatal: not a git repository".
#
# Pass --files-only to skip the Docker build (no daemon in some CI lanes).
set -euo pipefail

cd "$(dirname "$0")/.."
CAPSTONE="src/workshops/assistant/after"
FILES_ONLY=${1:-}

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

# A checkout with a commit in it. Both halves matter: `git archive HEAD` fails just
# as hard on a fresh `git init` as it does outside a repo.
if git rev-parse --git-dir >/dev/null 2>&1 && git rev-parse --verify -q HEAD >/dev/null; then
  LANE=git
  echo "==> Extracting src/ from HEAD"
  git archive --format=tar HEAD -- src | tar -x -C "$work"
else
  LANE=tree
  echo "==> No git checkout — treating this tree as the release extract"
  # The caches are excluded because they are the one thing here that a student
  # generated rather than received, and copying them in would let a local build
  # artifact stand in for a shipped file.
  tar -cf - \
    --exclude=.venv --exclude=__pycache__ --exclude='*.pyc' \
    --exclude=.pytest_cache --exclude=.ruff_cache --exclude=node_modules \
    src | tar -x -C "$work"
fi

echo "==> Checking the image's build inputs survived the archive"
missing=0
# Parse the COPY lines rather than hardcoding a list: a Dockerfile edit that adds a
# build input should fail here, not in a student's terminal three weeks later.
# `COPY --from=` moves files between build stages, so it has no repo file behind it.
while read -r src_path; do
  if [ ! -e "$work/$CAPSTONE/$src_path" ]; then
    if [ "$LANE" = git ]; then
      echo "error: $CAPSTONE/$src_path is COPYd by the Dockerfile but is not in HEAD" >&2
      echo "       (ignored by .gitignore? it needs a negation rule)" >&2
    else
      echo "error: $CAPSTONE/$src_path is COPYd by the Dockerfile but is not in this tree" >&2
      echo "       The release is incomplete — re-download it, or report it." >&2
    fi
    missing=1
  fi
done < <(awk '/^COPY / && !/--from=/ {for (i = 2; i < NF; i++) print $i}' "$CAPSTONE/Dockerfile")
[ "$missing" -eq 0 ] || exit 1

if [ "$LANE" = git ]; then
  echo "    all Dockerfile inputs are tracked"
else
  echo "    all Dockerfile inputs are present"
  # Named rather than glossed. Without git there is no "tracked", so a file the
  # release forgot and a file the student's own `uv sync` created look identical
  # from here — and that missing-uv.lock case is the bug this script was written
  # for. The build below is unaffected; only this check is weaker.
  echo "    note: presence, not provenance. Only the git lane can tell a shipped" >&2
  echo "          file from one your own runs left behind." >&2
fi

if [ "$FILES_ONLY" = "--files-only" ]; then
  echo
  echo "  release build inputs OK (skipped the image build) · $LANE lane"
  exit 0
fi

echo "==> Building the capstone image from the extract"
docker build -t genai-capstone:release-check "$work/$CAPSTONE"

echo
echo "  the shipped source builds a capstone image · $LANE lane"
