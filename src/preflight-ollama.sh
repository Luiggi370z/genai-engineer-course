#!/usr/bin/env bash
# Is the host's Ollama ready to be the stack's brain?
#
#   ./src/preflight-ollama.sh                          # the course model
#   ./src/preflight-ollama.sh --model qwen3.5:1.7b     # the CI wiring lane
#   ./src/preflight-ollama.sh --skip-container         # no docker on this box
#   ./src/preflight-ollama.sh --json facts.json        # version + digests, for attestation
#
# `verify-e2e.sh` runs this before Compose. It is separate, and executable on its
# own, because the question it answers is the one a learner hits first and the one
# a CI runner has to answer before it is worth building anything: the models live
# on the host now, and compose can neither start them nor wait for them.
#
# The checks themselves — and the reason each is a round trip rather than a
# lookup — are in phase8-deploy/01-compose/after/src/preflight.py. This is the
# wrapper: find a Python, run the module, pass the flags through.
#
# It never pulls. A preflight that fixes what it finds downloads six gigabytes on
# somebody's tethered connection without asking; this one prints the exact
# `ollama pull` and exits 1.
set -euo pipefail

cd "$(dirname "$0")"

MODULE_DIR="phase8-deploy/01-compose/after/src"

# The lesson's own venv if it has been built (`make -C phase8-deploy/01-compose/after
# install`), otherwise whatever python3 is on PATH. The module imports only the
# standard library precisely so the second case works: a preflight that needs a
# dependency installed before it can tell you what to install is a bootstrap
# problem wearing a check's clothes.
PYTHON="phase8-deploy/01-compose/after/.venv/bin/python"
[ -x "$PYTHON" ] || PYTHON="$(command -v python3 || true)"
if [ -z "$PYTHON" ]; then
  echo "preflight: no python3 on PATH — install Python 3.12+ and re-run" >&2
  exit 1
fi

echo "==> Preflight: the host's Ollama"
PYTHONPATH="$MODULE_DIR" exec "$PYTHON" -m preflight "$@"
