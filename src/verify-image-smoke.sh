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
# Three checks, cheapest first, all against the built image and not the checkout:
#   1. the application imports — the failure above, caught in under a second;
#   2. every provider the configuration OFFERS can actually be built and called;
#   3. the container starts and reports itself ready over HTTP.
#
# Check 2 is the same class of defect one layer out. `ASSISTANT_PROVIDER` documents
# `ollama | openai | anthropic | offline`, and for a while the image contained the
# SDKs for exactly one of them: `openai` was declared in the host-only `release`
# group and `anthropic` was not declared anywhere. Both selections booted fine and
# died on `ModuleNotFoundError` at the first request. A missing dependency that
# surfaces per request rather than at boot is the expensive kind — it looks like a
# bug in the code, and only the caller who picked that provider ever sees it.
#
# Check 3 needs no Qdrant, no Ollama and no model: with nothing configured the
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

echo "==> Selecting every advertised provider inside the image"
# Offline on purpose, and still a real test of the thing that was broken. Both SDKs
# read their base URL from the environment, so pointing them at a closed port means
# the call gets as far as opening a socket — which requires the package to be
# installed, importable and constructible — and then fails to connect. A connection
# error is a PASS here; an ImportError is the defect.
#
# The keys are obvious fakes. They are never sent anywhere: nothing on 127.0.0.1:1
# is listening, and the assertion below is about which exception came back.
#
# `-i`, and it is load-bearing: `docker run` without it gives `python -` an empty
# stdin, which exits 0 having read nothing. The first version of this check passed
# that way — a vacuous pass in the script written to catch a vacuous pass. Hence the
# sentinel below too: the check has to prove it ran, not just that it did not fail.
providers_out=$(docker run --rm -i \
  -e OPENAI_API_KEY=smoke-not-a-key -e OPENAI_BASE_URL=http://127.0.0.1:1/v1 \
  -e ANTHROPIC_API_KEY=smoke-not-a-key -e ANTHROPIC_BASE_URL=http://127.0.0.1:1 \
  "$IMAGE" python - <<'EOF'
from assistant import providers
from assistant.settings import Settings

for name, tag in ((providers.OPENAI, "gpt-4o-mini"), (providers.ANTHROPIC, "claude-sonnet-4-5")):
    chat = providers.build_chat(Settings(provider=name, chat_model=tag))
    assert chat is not None and chat.provider == name and chat.model == tag, chat
    try:
        chat.generate("ping")
    except ImportError as absent:  # the defect this check exists for
        raise SystemExit(f"{name} is advertised but its SDK is not in the image: {absent}")
    except Exception:
        pass  # anything else means the SDK loaded and tried to talk. That is the point.
    print(f"  {name} builds, imports its SDK and reaches the network layer ({tag})")

# The offline tier is a selection too, and it must NOT need either SDK.
assert providers.build_chat(Settings(provider=providers.OFFLINE)) is None
print("  offline selects the stitcher and imports nothing")
print("PROVIDERS-OK")
EOF
) || { printf '%s\n' "$providers_out"; die "the image cannot run a provider it advertises"; }
printf '%s\n' "${providers_out%PROVIDERS-OK}" | sed '/^$/d'
[[ "$providers_out" == *PROVIDERS-OK* ]] \
  || die "the provider check produced no verdict — it did not actually run"

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
