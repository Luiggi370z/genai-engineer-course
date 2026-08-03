#!/usr/bin/env bash
# Proves the capstone image can run the application it contains.
#
#   ./src/verify-image-smoke.sh              # build, then smoke it
#   ./src/verify-image-smoke.sh --no-build   # smoke an image you already built
#
# This exists because a build that succeeds proves only that the files copied.
# The round-5 release shipped an image that built perfectly and could not start:
# `provenance.py` computed its source root at import time with
# `Path(__file__).resolve().parents[5]`, which is right in the checkout — thirteen
# parents — and `IndexError` at `/app/src/assistant/provenance.py`, which has four.
# `api.py` imports that module, so Uvicorn died before startup and Docker restarted
# the container until someone looked. Every gate in the repo was green.
#
# The lesson for Phase 8, and the reason this is a shipped script rather than three
# lines of CI YAML: **provenance proves which artifact ran; it cannot prove the
# artifact runs.** Packaging checks, hash manifests and source binding all answer
# "is this the code we meant to ship". None of them answer "does it boot".
#
# Two checks, cheapest first, both against the built image and not the checkout:
#   1. the application imports — the failure above, caught in under a second;
#   2. the container starts and reports itself ready over HTTP.
#
# Check 2 needs no Qdrant, no Ollama and no model: with nothing configured the
# assistant falls to its rule-based tier, which `warm()` reports ready immediately.
# That is the point — this asks whether the process can serve, not whether the
# model is good, and it costs a couple of seconds instead of twenty minutes.
set -euo pipefail

cd "$(dirname "$0")/.."
CAPSTONE="src/workshops/assistant/after"
IMAGE=${IMAGE:-capstone:smoke}
CONTAINER=${CONTAINER:-capstone-smoke}
# Not 8000: a developer running this almost certainly has the real stack up.
PORT=${PORT:-18000}
READY_TIMEOUT=${READY_TIMEOUT:-60}

die() { printf 'FAIL: %s\n' "$1"; exit 1; }

if [ "${1:-}" != "--no-build" ]; then
  echo "==> Building $IMAGE"
  docker build -t "$IMAGE" "$CAPSTONE" >/dev/null || die "the image did not build"
fi

echo "==> Importing the application inside the image"
# Every module the two entrypoints reach: the API (default CMD), the MCP server
# (command override in compose), the report the CI evidence job runs, and the
# release lane. Import-time work is what broke, so importing IS the test.
docker run --rm "$IMAGE" python -c "
import assistant.api, assistant.mcp_server, assistant.release, assistant.report
" || die "the image cannot import its own application — see the traceback above"
echo "  assistant.api, .mcp_server, .release, .report all import"

echo "==> Starting the container and waiting for /ready"
docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
docker run -d --name "$CONTAINER" -p "$PORT:8000" "$IMAGE" >/dev/null \
  || die "the container did not start"
# shellcheck disable=SC2317 # called via trap
cleanup() { docker rm -f "$CONTAINER" >/dev/null 2>&1 || true; }
trap cleanup EXIT

base="http://localhost:$PORT"
deadline=$((SECONDS + READY_TIMEOUT))
until curl -sf "$base/ready" -o /tmp/image-smoke-ready.json 2>/dev/null; do
  # The state, not just the clock. A crash-looping container never answers, and
  # waiting out the timeout to say "not ready" hides the traceback that says why.
  status=$(docker inspect -f '{{.State.Status}}' "$CONTAINER" 2>/dev/null || echo gone)
  restarts=$(docker inspect -f '{{.RestartCount}}' "$CONTAINER" 2>/dev/null || echo 0)
  if [ "$status" != "running" ] || [ "$restarts" != "0" ]; then
    docker logs --tail 40 "$CONTAINER" 2>&1 || true
    die "the assistant container is $status after $restarts restart(s) — see above"
  fi
  ((SECONDS < deadline)) || {
    docker logs --tail 40 "$CONTAINER" 2>&1 || true
    die "the container never reported ready within ${READY_TIMEOUT}s"
  }
  sleep 1
done

curl -sf "$base/health" -o /tmp/image-smoke-health.json || die "/ready answered but /health did not"
python3 - <<'EOF' || die "/health is not the shape the deploy probes read"
import json
health = json.load(open("/tmp/image-smoke-health.json"))
missing = [k for k in ("status", "version", "tier", "ready") if k not in health]
assert not missing, f"/health is missing {missing}"
assert health["ready"] is True, health
print(f"  /health ok — version {health['version']}, brain {health['tier']['brain']}")
EOF

echo
echo "image smoke: the artifact imports, starts, and serves /ready"
