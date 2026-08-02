#!/usr/bin/env bash
# Publish an immutable image, deploy it, prove it, and undo it if it lied.
#
#   DEPLOY_LANE=fly FLY_APP=my-assistant ./deploy/release.sh
#
# NOT LIVE-PROVISIONED: no account, no card, nothing here has run against Fly by
# this repo. It is gated off exactly the way the OAuth and guard-model lanes are,
# so the default `make check` never touches a network.
#
# The shape worth stealing, whatever your provider: this script owns four `fly`
# commands and NO judgement. Every decision — is the tag safe, did the smoke
# pass, what do we roll back to — lives in `src/release.py`, where it is unit
# tested. A rollback trigger that has never run is one that fires for the first
# time during an incident.
set -euo pipefail
cd "$(dirname "$0")/.."

[[ "${DEPLOY_LANE:-off}" == "fly" ]] || {
  echo "deploy lane off. Set DEPLOY_LANE=fly FLY_APP=<app> to arm it." >&2
  exit 0
}
: "${FLY_APP:?set FLY_APP to your app name}"
command -v flyctl >/dev/null || { echo "flyctl not on PATH: https://fly.io/docs/flyctl/install" >&2; exit 1; }

REGISTRY="registry.fly.io"
SHA="$(git rev-parse HEAD)"
DIRTY=""; [[ -n "$(git status --porcelain)" ]] && DIRTY="--dirty"

# 1. IDENTITY. Refuses a dirty tree and any tag that is not a commit, so the
#    thing in the registry can always be traced back to a commit that exists.
IMAGE="$(python src/release.py tag --registry "$REGISTRY/$FLY_APP" --sha "$SHA" $DIRTY)"
echo "==> $IMAGE"

# 2. SECRETS, bound by name from the platform store. Set once, out of band; never
#    in fly.toml, never in the image, never in this file. Listing them here is the
#    audit answer to "what can this service read?" without disclosing any of it.
SECRETS=(JWT_SIGNING_KEY TELEGRAM_BOT_TOKEN OPENAI_API_KEY)
for name in "${SECRETS[@]}"; do
  flyctl secrets list --app "$FLY_APP" | grep -q "^$name" \
    || echo "warn: $FLY_APP has no secret named $name (flyctl secrets set $name=...)" >&2
done

# The release we would fall back to, captured BEFORE we replace it. Asking
# afterwards means asking a system you have just broken.
PREVIOUS="$(flyctl releases --app "$FLY_APP" --json 2>/dev/null \
  | python -c 'import json,sys; r=json.load(sys.stdin); print(r[0]["ImageRef"] if r else "")' || true)"

# 3. BUILD + PUBLISH, then deploy that exact digest. Two steps rather than one so
#    the image that passed CI is the image that ships — `fly deploy` building its
#    own is how a green pipeline deploys code the pipeline never saw.
flyctl deploy --app "$FLY_APP" --config deploy/fly.toml --image-label "${IMAGE##*:}" --build-only --push
flyctl deploy --app "$FLY_APP" --config deploy/fly.toml --image "$IMAGE" --strategy rolling

# 4. SMOKE. Four probes, and the one that matters most asks /health which SHA it
#    is serving: a half-finished deploy leaves an old machine in the pool, and it
#    is a perfectly healthy service that passes every other check.
URL="https://${FLY_APP}.fly.dev"
if DEPLOY_SMOKE_TOKEN="${DEPLOY_SMOKE_TOKEN:-}" python src/release.py verify --url "$URL" --sha "$SHA"; then
  echo "==> promoted $IMAGE"
  exit 0
fi

# 5. UNDO. Only to a previous immutable tag; `decide()` returns "halt" when there
#    isn't one, because a script that pretends to recover turns a bad deploy into
#    an outage nobody is looking at.
echo "==> smoke failed" >&2
if [[ -n "$PREVIOUS" ]]; then
  flyctl deploy --app "$FLY_APP" --config deploy/fly.toml --image "$PREVIOUS" --strategy immediate
  echo "==> rolled back to $PREVIOUS" >&2
else
  echo "==> HALT: nothing immutable to roll back to. The broken release is still up," >&2
  echo "    which is visible and therefore better than a silent no-op. Page someone." >&2
fi
exit 1
