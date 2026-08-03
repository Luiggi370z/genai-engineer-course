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
# Six checks, cheapest first:
#
#   0. dist/BUILD.json declares a schema this script understands, and carries the
#      release metadata — version, build time, toolchain — rather than only hashes
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
#: The stamp schema this script knows how to read. See SCHEMA_VERSION in package.sh.
SCHEMA_VERSION=1

if [ ! -f "$STAMP" ]; then
  echo "error: no $STAMP — run ./package.sh to build a release first" >&2
  exit 1
fi

fail=0
note() {
  echo "error: $1" >&2
  fail=1
}

# 0. The metadata, before anything is read out of the stamp on the assumption that
# its keys still mean what this script thinks. A stamp with no `schema_version` is
# from a package.sh that predates it; a higher one is from a newer package.sh and
# this script has no business guessing at it.
if ! python3 - "$STAMP" "$SCHEMA_VERSION" <<'PY'
import datetime as dt, json, re, sys

path, known = sys.argv[1], int(sys.argv[2])
stamp = json.load(open(path))
bad = []

declared = stamp.get("schema_version")
if declared is None:
    bad.append(
        "no schema_version — this stamp predates release metadata. Re-run ./package.sh."
    )
elif not isinstance(declared, int):
    bad.append(f"schema_version is {declared!r}, which is not an integer")
elif declared > known:
    bad.append(
        f"schema_version {declared} is newer than the {known} this script reads. "
        "Update verify-dist.sh rather than trusting a stamp you cannot parse."
    )

for key in ("version", "version_source"):
    if not str(stamp.get(key, "")).strip():
        bad.append(f"{key} is missing or empty")

built = str(stamp.get("built_at", ""))
if not built:
    bad.append("built_at is missing")
elif not built.endswith("Z"):
    bad.append(f"built_at is {built!r} — a release timestamp has to state its zone")
else:
    try:
        when = dt.datetime.fromisoformat(built.replace("Z", "+00:00"))
    except ValueError:
        bad.append(f"built_at is {built!r}, which is not an ISO-8601 instant")
    else:
        # A stamp from the future is a clock problem, and it silently breaks any
        # later attempt to order two releases by when they were built.
        ahead = (when - dt.datetime.now(dt.UTC)).total_seconds()
        if ahead > 300:
            bad.append(f"built_at is {round(ahead / 60)} minute(s) in the future")

toolchain = stamp.get("toolchain")
if not isinstance(toolchain, dict):
    bad.append("toolchain is missing")
else:
    for tool in ("node", "pnpm", "python", "uv", "git"):
        if not str(toolchain.get(tool, "")).strip():
            bad.append(f"toolchain.{tool} is missing")
    # `node` and `pnpm` built course.html. If either is "absent" the stamp is
    # describing a build that could not have happened.
    for tool in ("node", "pnpm", "python", "git"):
        if str(toolchain.get(tool, "")) == "absent":
            bad.append(f"toolchain.{tool} is 'absent', but package.sh cannot run without it")
    for tool, value in toolchain.items():
        if value != "absent" and not re.search(r"\d+\.\d+", str(value)):
            bad.append(f"toolchain.{tool} is {value!r}, which carries no version number")

for line in bad:
    print(f"error: {path}: {line}", file=sys.stderr)
if bad:
    raise SystemExit(1)
print(
    f"    stamp schema {declared} · version {stamp['version']} "
    f"(from {stamp['version_source']}) · built {built}"
)
PY
then
  fail=1
fi

# The tag is authoritative at release time, so when there is one it and the stamp
# have to agree — and so does `app/package.json`, which is the number the stamp
# falls back to off a tag. Two sources for one version with no tie-break is how a
# release ends up called two things at once.
if tag=$(git describe --exact-match --tags HEAD 2>/dev/null); then
  stamped_version=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' "$STAMP")
  if [ "$stamped_version" != "$tag" ]; then
    note "HEAD is tagged $tag but the stamp says $stamped_version — run ./package.sh on the tag"
  fi
  declared=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' app/package.json)
  if [ "${tag#v}" != "$declared" ]; then
    note "tag $tag and app/package.json $declared disagree — bump package.json to ${tag#v}"
  fi
fi

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
