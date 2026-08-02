#!/usr/bin/env bash
# Is what is committed under dist/ this commit's release, or a stale one?
#
#   ./verify-dist.sh
#
# Runs in CI on every push. A minified bundle looks equally plausible whatever it
# was built from, so "the workbook is up to date" is not a question you can answer
# by opening the file — which is how a release ships with three-week-old content
# and nobody notices until a student asks why a lesson in the zip is not in the
# workbook.
#
# Four checks, cheapest first:
#
#   1. dist/BUILD.json exists and names a commit git knows
#   2. the src/, app/ and release/ trees it was built from are the trees at HEAD —
#      content, not commits, so a docs-only commit does not invalidate a good dist
#   3. the committed artifacts still hash to what the stamp recorded (nobody
#      hand-edited course.html, and no partial copy landed)
#   4. the zip carries exactly the files `git archive HEAD -- src` would produce
#
# Deliberately *not* a byte-for-byte rebuild of course.html. A bundler's output
# depends on its own version, so that check would fail on a Node upgrade with a
# diff nobody can read, and the fix would be to delete the check. Comparing trees
# and hashes catches the failure that actually happens — a dist nobody rebuilt —
# without pretending the build is bit-reproducible across machines.
set -euo pipefail

cd "$(dirname "$0")"

NAME="genai-engineer-workbook-src"
STAMP="dist/BUILD.json"

if [ ! -f "$STAMP" ]; then
  echo "error: no $STAMP — run ./package.sh and commit dist/" >&2
  exit 1
fi

fail=0
note() {
  echo "error: $1" >&2
  fail=1
}

commit=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["commit"])' "$STAMP")
if ! git cat-file -e "$commit^{commit}" 2>/dev/null; then
  note "$STAMP names commit $commit, which is not in this repository"
  exit 1
fi

echo "==> dist/ was built from ${commit:0:12}"

# 2. the trees, not the commit. `dist/` and `.github/` change without changing
# anything a student receives; requiring an exact commit match would make every
# CI tweak look like a stale release and teach everyone to ignore this.
for prefix in src app release; do
  want=$(git rev-parse "HEAD:$prefix")
  got=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["trees"].get(sys.argv[2], ""))' "$STAMP" "$prefix")
  if [ "$want" != "$got" ]; then
    note "$prefix/ at HEAD is ${want:0:12} but dist/ was built from ${got:0:12} — run ./package.sh"
  fi
done

# 3. the artifacts are the ones that were stamped.
while read -r artifact expected; do
  [ -n "$artifact" ] || continue
  if [ ! -f "dist/$artifact" ]; then
    note "dist/$artifact is in the stamp but missing from dist/"
    continue
  fi
  actual=$(shasum -a 256 "dist/$artifact" | cut -d' ' -f1)
  if [ "$actual" != "$expected" ]; then
    note "dist/$artifact does not match its stamp — it was edited or partly copied"
  fi
done < <(python3 -c '
import json, sys
for name, digest in json.load(open(sys.argv[1]))["artifacts"].items():
    print(name, digest)
' "$STAMP")

# 4. the zip is HEAD'"'"'s src/. Compared by file list rather than by bytes: zip
# entries carry timestamps and a compression level, so two archives of identical
# content differ byte-wise across git versions.
shipped=$(mktemp)
expected=$(mktemp)
trap 'rm -f "$shipped" "$expected"' EXIT
# Directory entries and the archive's own prefix entry are not files; dropping
# them is what makes this comparable to `git ls-tree`, which only lists blobs.
unzip -Z1 "dist/$NAME.zip" | sed "s|^$NAME/||" | grep -Ev '(/$|^$)' | sort >"$shipped"
git ls-tree -r --name-only HEAD -- src | sort >"$expected"
if ! diff -q "$shipped" "$expected" >/dev/null; then
  note "the zip does not carry HEAD's src/. First differences:"
  diff "$expected" "$shipped" | head -20 >&2
fi

if [ "$fail" -ne 0 ]; then
  echo >&2
  echo "dist/ is stale or hand-edited. ./package.sh rebuilds all of it from one commit." >&2
  exit 1
fi

echo "    trees match HEAD · artifacts match their hashes · zip carries HEAD's src/"
echo
echo "  dist/ is this commit's release"
