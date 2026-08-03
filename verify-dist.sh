#!/usr/bin/env bash
# Is the dist/ on this machine the release of the commit you are on?
#
#   ./verify-dist.sh
#
# Run it before you upload. dist/ is a build artifact and is NOT in the repository
# — it is reproduced from any commit by ./package.sh — so nothing here is a CI
# concern: there is no committed release that could go stale, which is most of the
# reason not to commit one. What remains is the local mistake, and it is an easy
# one: package a release, keep working, then publish the dist/ still sitting in
# your working directory a dozen commits later. A minified bundle looks equally
# plausible whatever it was built from, so opening the file cannot tell you.
#
# Five checks, cheapest first:
#
#   1. dist/BUILD.json exists and names a commit git knows
#   2. the src/, app/ and release/ trees it was built from are the trees at HEAD —
#      content, not commits, so a docs-only commit does not invalidate a good dist
#   3. the artifacts still hash to what the stamp recorded (nobody hand-edited
#      course.html, and no partial copy landed)
#   4. every member of the zip has the same content as HEAD's src/ — each file's
#      own sha256, recorded in the stamp at package time, checked against both
#      the archive and `git archive HEAD` — plus the one generated member
#      (src/RELEASE_COMMIT), which has to name the same commit as the stamp
#   5. the shipped verifier resolves that commit from an extracted zip with no
#      repository above it
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
  echo "error: no $STAMP — run ./package.sh to build a release first" >&2
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

# 4. the zip is HEAD's src/, member by member and byte for byte inside each
# member. Not by file list: a list says a lesson is present, not that the file
# under that name is the one you wrote, and "present but wrong" is the failure a
# student would hit rather than "missing". And not by hashing the archive — that
# is check 3's job and it is a different question, since rezipping identical
# content under another git or compression level changes the archive's bytes.
#
# Three dictionaries have to agree: the `files` manifest in the stamp, the
# archive sitting in dist/, and `git archive HEAD -- src`. Comparing the stamp to
# both ends means a mismatch says which side moved — a rezipped dist, or a stamp
# recorded before an edit.
if ! python3 - "$STAMP" "dist/$NAME.zip" "$NAME" "$commit" <<'PY'
import hashlib, io, json, subprocess, sys, tarfile, zipfile

stamp_path, zip_path, name, commit = sys.argv[1:5]
stamp = json.load(open(stamp_path))

manifest = stamp.get("files")
if not manifest:
    print(
        f"error: {stamp_path} has no per-member manifest — it was built by a "
        "package.sh from before content verification existed. Re-run ./package.sh.",
        file=sys.stderr,
    )
    raise SystemExit(1)


def digests(pairs):
    return {path: hashlib.sha256(blob).hexdigest() for path, blob in pairs}


with zipfile.ZipFile(zip_path) as zf:
    shipped = digests(
        (info.filename.removeprefix(f"{name}/"), zf.read(info))
        for info in zf.infolist()
        if not info.is_dir()
    )

# `git archive` rather than a checkout of the working tree: HEAD is what the
# release claims to be, and the working tree is allowed to differ mid-session.
# One subprocess for all ~700 files, because a `git cat-file` per member turns a
# pre-upload check into something people skip.
archived = subprocess.run(
    ["git", "archive", "--format=tar", "HEAD", "--", "src"],
    capture_output=True,
    check=True,
).stdout
with tarfile.open(fileobj=io.BytesIO(archived)) as tf:
    head = digests(
        (member.name, tf.extractfile(member).read())
        for member in tf.getmembers()
        if member.isfile()
    )
# The one generated member. Its content is the commit and a newline — the same
# string package.sh writes — so it is checked like any other file rather than
# trusted because it is generated.
head["src/RELEASE_COMMIT"] = hashlib.sha256(f"{commit}\n".encode()).hexdigest()


def report(what, expected, actual):
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    changed = sorted(p for p in set(expected) & set(actual) if expected[p] != actual[p])
    if not (missing or extra or changed):
        return 0
    for label, paths in (("missing from", missing), ("not in", extra), ("differs in", changed)):
        if paths:
            print(f"error: {len(paths)} file(s) {label} {what}:", file=sys.stderr)
            for path in paths[:10]:
                print(f"         {path}", file=sys.stderr)
            if len(paths) > 10:
                print(f"         … and {len(paths) - 10} more", file=sys.stderr)
    return 1


bad = report("the shipped zip", manifest, shipped)
bad |= report("HEAD's src/", head, manifest)
if bad:
    raise SystemExit(1)
print(f"    {len(manifest)} zip members match HEAD's src/ by content")
PY
then
  note "the zip's contents are not HEAD's src/ — run ./package.sh"
fi

# And it has to name the right commit, or it is worse than absent: the shipped
# E2E would confidently expect an image built from something else. The manifest
# above proves the bytes are some commit's; this says which.
stamped=$(unzip -p "dist/$NAME.zip" "$NAME/src/RELEASE_COMMIT" 2>/dev/null | tr -d '[:space:]')
if [ "$stamped" != "$commit" ]; then
  note "the zip's src/RELEASE_COMMIT says '${stamped:-<missing>}', the stamp says ${commit:0:12}"
fi

# 5. the shipped verifier works where the student runs it: an extracted ZIP with
# no repository anywhere above it. The release README advertises the unqualified
# `./verify-e2e.sh`, and that script used to read its commit straight from git —
# which produced an empty expectation in the ZIP and failed a check on a healthy
# stack. Nothing catches that from inside a checkout, where git always answers,
# so the check has to leave the checkout.
sandbox=$(mktemp -d)
trap 'rm -rf "$sandbox"' EXIT
unzip -q "dist/$NAME.zip" -d "$sandbox"
# Asking the shipped script rather than reimplementing its logic here: a copy of
# the resolution would pass while the real one failed, which is how the original
# defect survived review. `--print-commit` stops before Docker is touched.
# Ceiling the search makes "no repository above" a fact rather than a hope about
# wherever mktemp landed.
resolved=$(GIT_CEILING_DIRECTORIES="$sandbox" GIT_SHA= \
  bash "$sandbox/$NAME/src/verify-e2e.sh" --print-commit)
if [ "$resolved" != "$commit" ]; then
  note "the extracted ZIP resolves its commit as '${resolved}', not ${commit:0:12} —"
  note "  verify-e2e.sh cannot tell which code it is testing outside a checkout"
fi

if [ "$fail" -ne 0 ]; then
  echo >&2
  echo "dist/ is stale or hand-edited. ./package.sh rebuilds all of it from one commit." >&2
  exit 1
fi

echo "    trees match HEAD · artifacts match their hashes · every zip member's content matches HEAD"
echo "    the extracted ZIP knows its own commit without git"
echo
echo "  dist/ is this commit's release"
