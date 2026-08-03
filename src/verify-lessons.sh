#!/usr/bin/env bash
# Verifies every lesson in the companion repo.
#
#   ./verify-lessons.sh                  every after/  : sync + lint + test + type must pass
#   ./verify-lessons.sh --before         every before/ : lint + type pass, tests fail BY DESIGN
#   ./verify-lessons.sh --python 3.11    the same, on exactly that interpreter
#
# "BY DESIGN" is the load-bearing part and is now checked rather than assumed: the
# suite has to collect, the run has to exit 1 rather than any other nonzero code,
# and the failures have to be the sort a student removes by writing code. See
# before-contract.py.
#
# `--python` exists because `requires-python = ">=3.11,<3.15"` is a claim, and
# without it nothing in this repo tested the ends of that range: uv picks the newest
# interpreter it can find, so every run proved the ceiling by accident and the floor
# never. It pins the interpreter and SKIPS any lesson whose own `requires-python`
# excludes that version — which is one lesson, the framework bakeoff, pinned to 3.12
# because CrewAI breaks on Chroma's Pydantic v1 shim above it. Skipped lessons are
# named in the summary; a run where nothing was verified fails.
#
# Needs uv on PATH (https://docs.astral.sh/uv/). Nothing here touches the network
# beyond `uv sync`; integration tests are excluded on purpose.
set -uo pipefail

cd "$(dirname "$0")" || exit 1
export PATH="$HOME/.local/bin:$PATH"

command -v uv >/dev/null || { echo "uv not found on PATH"; exit 1; }

MODE="after"
PYVER=""
while (($#)); do
  case "$1" in
    --before) MODE="before" ;;
    --python)
      PYVER="${2:-}"
      [[ "$PYVER" =~ ^3\.[0-9]+$ ]] || { echo "usage: --python 3.11 (major.minor)"; exit 1; }
      shift
      ;;
    *) echo "unknown argument: $1"; exit 1 ;;
  esac
  shift
done

# uv reads this for both `sync` and `run`, so one export covers every step below.
[[ -n "$PYVER" ]] && export UV_PYTHON="$PYVER"

# Whether a lesson's own `requires-python` admits the version being tested. Answered
# by the lesson's manifest rather than by a list kept here, because a list of
# exceptions in the runner is a list that goes stale the first time a lesson changes
# its mind. An operator this cannot evaluate exits 2 and is treated as a failure —
# guessing would silently skip a lesson that should have run.
supports_python() {
  python3 - "$1" "$2" <<'PY'
import re
import sys

spec = ""
for line in open(sys.argv[1], encoding="utf-8"):
    found = re.match(r'\s*requires-python\s*=\s*"([^"]+)"', line)
    if found:
        spec = found.group(1)
        break

def parts(text):
    return tuple(int(p) for p in re.findall(r"\d+", text))

target = parts(sys.argv[2])
for clause in (c.strip() for c in spec.split(",")):
    if not clause:
        continue
    found = re.match(r"(>=|<=|==|!=|>|<)\s*(.+)", clause)
    if not found:
        sys.exit(2)
    op, want = found.group(1), parts(found.group(2))
    width = max(len(want), len(target))
    got = target + (0,) * (width - len(target))
    want += (0,) * (width - len(want))
    ok = {
        ">=": got >= want, "<=": got <= want, "==": got == want,
        "!=": got != want, ">": got > want, "<": got < want,
    }[op]
    if not ok:
        sys.exit(1)
sys.exit(0)
PY
}

# One directory for every JUnit report, removed on the way out however this exits.
# Per-lesson files rather than one reused name so a failure can be re-read.
CONTRACT="$PWD/before-contract.py"
SCRATCH="$(mktemp -d)"
trap 'rm -rf "$SCRATCH"' EXIT
if [[ "$MODE" == "before" && ! -f "$CONTRACT" ]]; then
  echo "before-contract.py is missing from $PWD — the --before lane cannot judge a scaffold without it"
  exit 1
fi

pass=0
fail=0
failures=()
skipped=()

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
#
# "The tests must fail" was the whole check for a long time, and it is not enough.
# `pytest` exits nonzero for a missing import, a syntax error, a conftest that
# raises, a plugin that will not load, and a suite that collected nothing — so a
# scaffold nobody could finish reported OK next to one that was fine. Two steps
# close it: collection has to succeed on its own, and the failures have to be the
# kind a student removes by writing code. `before-contract.py` holds the second
# line and explains the allowed set.
check_before() {
  local dir="$1"
  ( cd "$dir" || exit 1
    uv sync --quiet   >/dev/null 2>&1 || { echo "SYNC"; exit 1; }
    uv run ruff check . >/dev/null 2>&1 || { echo "LINT"; exit 1; }
    uv run pyright    >/dev/null 2>&1 || { echo "TYPE"; exit 1; }
    # First, because everything after it assumes the suite can be loaded at all.
    # This is the step that separates "red by design" from "does not import".
    uv run pytest -q --collect-only -m "not integration" >/dev/null 2>&1 \
      || { echo "COLLECT"; exit 1; }
    local report="$SCRATCH/$(printf '%s' "$dir" | tr -c 'A-Za-z0-9' '-').xml"
    # `--tb=no` because nothing reads the traceback: the XML carries the exception
    # type per test, which is the only thing the contract needs.
    uv run pytest -q --tb=no -m "not integration" --junit-xml="$report" >/dev/null 2>&1
    local code=$?
    # 1 is "tests failed", which is the goal. 2-5 are interrupted, internal error,
    # usage error and nothing-collected — every one of them nonzero, and every one
    # of them previously indistinguishable from success here.
    ((code == 1)) || { echo "RUN-EXIT-$code"; exit 1; }
    local reason
    reason="$(python3 "$CONTRACT" "$report")" || { echo "${reason:-CONTRACT}"; exit 1; }
  )
}

while IFS= read -r pyproject; do
  dir="$(dirname "$pyproject")"
  printf '%-58s ' "$dir"
  if [[ -n "$PYVER" ]]; then
    supports_python "$pyproject" "$PYVER"
    case $? in
      0) ;;
      1)
        echo "SKIP (needs $(sed -n 's/.*requires-python *= *"\([^"]*\)".*/\1/p' "$pyproject"))"
        skipped+=("$dir")
        continue
        ;;
      *)
        echo "FAIL (REQUIRES-PYTHON unreadable)"
        fail=$((fail + 1))
        failures+=("$dir [REQUIRES-PYTHON unreadable]")
        continue
        ;;
    esac
  fi
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
echo "${MODE}${PYVER:+ on python $PYVER}: ${pass} passed, ${fail} failed${skipped[0]+, ${#skipped[@]} skipped}"
if ((${#skipped[@]} > 0)); then
  printf '  skipped: %s\n' "${skipped[@]}"
fi
if ((fail > 0)); then
  printf '  %s\n' "${failures[@]}"
  exit 1
fi
# A version nothing supports would otherwise report "0 passed, 0 failed" and exit 0,
# which is the shape of a green CI job that tested nothing.
if ((pass == 0)); then
  echo "  nothing was verified — every lesson was skipped or none was found"
  exit 1
fi
