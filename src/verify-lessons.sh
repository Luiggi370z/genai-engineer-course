#!/usr/bin/env bash
# Verifies every lesson in the companion repo.
#
#   ./verify-lessons.sh            every after/  : sync + lint + test + type must pass
#   ./verify-lessons.sh --before   every before/ : lint + type pass, tests fail BY DESIGN
#
# Needs uv on PATH (https://docs.astral.sh/uv/). Nothing here touches the network
# beyond `uv sync`; integration tests are excluded on purpose.
set -uo pipefail

cd "$(dirname "$0")" || exit 1
export PATH="$HOME/.local/bin:$PATH"

command -v uv >/dev/null || { echo "uv not found on PATH"; exit 1; }

MODE="after"
[[ "${1:-}" == "--before" ]] && MODE="before"

pass=0
fail=0
failures=()

check_after() {
  local dir="$1"
  ( cd "$dir" || exit 1
    uv sync --quiet   >/dev/null 2>&1 || { echo "SYNC"; exit 1; }
    uv run ruff check . >/dev/null 2>&1 || { echo "LINT"; exit 1; }
    uv run pytest -q -m "not integration" >/dev/null 2>&1 || { echo "TEST"; exit 1; }
    uv run pyright    >/dev/null 2>&1 || { echo "TYPE"; exit 1; }
  )
}

# A before/ scaffold is correct when it is clean but incomplete: lint and type must
# pass so the student starts from a green baseline, while the tests must fail.
check_before() {
  local dir="$1"
  ( cd "$dir" || exit 1
    uv sync --quiet   >/dev/null 2>&1 || { echo "SYNC"; exit 1; }
    uv run ruff check . >/dev/null 2>&1 || { echo "LINT"; exit 1; }
    uv run pyright    >/dev/null 2>&1 || { echo "TYPE"; exit 1; }
    if uv run pytest -q -m "not integration" >/dev/null 2>&1; then
      echo "TESTS-PASS-UNEXPECTEDLY"; exit 1
    fi
  )
}

while IFS= read -r pyproject; do
  dir="$(dirname "$pyproject")"
  printf '%-58s ' "$dir"
  if [[ "$MODE" == "after" ]]; then
    reason="$(check_after "$dir")"
  else
    reason="$(check_before "$dir")"
  fi
  if [[ -z "$reason" ]]; then
    echo "OK"
    pass=$((pass + 1))
  else
    echo "FAIL ($reason)"
    fail=$((fail + 1))
    failures+=("$dir [$reason]")
  fi
done < <(
  # -prune keeps us out of installed packages: a synced .venv is full of
  # third-party pyproject.toml files (pandas ships one), and each would be
  # picked up as a "lesson".
  find . -name .venv -prune -o -name pyproject.toml -path "*/${MODE}/*" -print | sort
)

echo
echo "${MODE}: ${pass} passed, ${fail} failed"
if ((fail > 0)); then
  printf '  %s\n' "${failures[@]}"
  exit 1
fi
