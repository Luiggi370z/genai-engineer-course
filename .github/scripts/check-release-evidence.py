#!/usr/bin/env python3
"""Refuse to publish a release whose evidence is about something else.

    python3 .github/scripts/check-release-evidence.py --source "$(...)" [--commit SHA]

Three artifacts are committed by hand because the measurement needs a GPU and a
hosted runner has none: `release-report.json` (the numbers), `RELEASE-EVIDENCE.md`
(the page quoting them) and `e2e-attestation.json` (proof the deployed stack passed
its end-to-end suite). Hand-carried evidence is only worth anything if something
checks that it describes *this* source, so this does, in five ways:

  1. the report is bound to the source being published, and that binding is a real
     one — `dirty-` and `unbound` are refusals, not values, and they compare equal
     to each other, so they are rejected before any comparison;
  2. `gate.py`'s four thresholds — quality, safety, latency, cost — reapplied over
     the committed numbers. Imported from the lesson rather than restated here: a
     second copy of a threshold is a threshold that will disagree with itself;
  3. the page is stapled to the JSON by digest, so a page quoting an older run
     cannot ride along with fresher numbers;
  4. the end-to-end suite ran to completion — every check, none skipped;
  5. it ran on the lane the release claims, not the fast CI overlay.

Stdlib only, and no `uv sync`: this runs on a bare runner before anything is built.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EVIDENCE = REPO / "release" / "evidence"
GATE_PATH = REPO / "src" / "phase8-deploy" / "02-ci" / "after" / "src" / "gate.py"

# The lane that runs the real model, by the prefix it writes into its own
# attestation. An allowlist rather than a ban on the CI overlay: a lane added
# later should have to be admitted deliberately, not admitted by not matching a
# string. `--ci` runs a 1.7B to prove wiring and says so in its own lane name, and
# letting it attest a release would publish "the deployed stack passes" on the
# strength of a run that was never meant to answer that question.
#
# One entry now, where there used to be two. The in-stack lane was accepted as the
# stronger claim — self-contained, no host dependencies — but it ran the 9B on CPU
# inside a VM at 0.52 tokens/second, so what it actually measured was the offline
# fallback with a fifteen-minute timeout hiding it. A lane whose numbers describe
# a tier the release does not ship cannot carry the release claim.
RELEASE_LANES = ("host ollama",)

#: What the attestation has to say about the model beyond its tag. A tag is a
#: mutable pointer: `qwen3.5:9b` a year from now may not be the bytes these
#: numbers were measured against, and without the digest nobody can tell.
REQUIRED_MODEL_FACTS = ("ollama_version", "model_digests")

# An id that is not a binding. Equal to each other, which is why nothing may be
# compared before they are excluded.
UNBINDABLE = ("dirty-", "unbound")


def load_gate():
    """`gate.py` by path, because it lives in a lesson and has no package.

    Registered in `sys.modules` before it executes: `@dataclass` resolves a
    class's annotations through `sys.modules[cls.__module__]`, and a module that
    is not in there yet gets `None` and an `AttributeError` from inside
    `dataclasses`, which is a confusing way to learn about import machinery.
    """
    name = "release_gate"
    spec = importlib.util.spec_from_file_location(name, GATE_PATH)
    if spec is None or spec.loader is None:  # pragma: no cover - a moved lesson
        raise SystemExit(f"cannot load the merge gates from {GATE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        del sys.modules[name]
        raise
    return module


def unbindable(value: str) -> bool:
    return value == "unbound" or value.startswith("dirty-")


def problems(source: str, commit: str | None, evidence: Path = EVIDENCE) -> list[str]:
    found: list[str] = []
    if unbindable(source):
        return [f"this checkout has no bindable source id ({source})"]

    json_path = evidence / "release-report.json"
    page_path = evidence / "RELEASE-EVIDENCE.md"
    attestation_path = evidence / "e2e-attestation.json"
    missing = [p.name for p in (json_path, page_path, attestation_path) if not p.is_file()]
    if missing:
        return [f"no committed evidence in {evidence}: {', '.join(missing)}"]

    body = json_path.read_bytes()
    page = page_path.read_text()
    data = json.loads(body)
    attestation = json.loads(attestation_path.read_text())

    # 1. the numbers are about this source
    measured = str(data.get("versions", {}).get("source", "<none>"))
    print(f"the committed numbers measured: {measured}")
    if unbindable(measured):
        found.append(f"the evidence is not bound to committed code ({measured})")
    elif measured != source:
        found.append(f"the evidence measured {measured}, this release is {source}")

    # 2. the thresholds, reapplied
    gate = load_gate()
    allowed, reasons = gate.should_merge(gate._load(json_path))
    print(f"merge gates over the committed numbers: {'pass' if allowed else 'BLOCKED'}")
    found.extend(f"the committed numbers do not clear the merge gate: {r}" for r in reasons)

    # 3. the page quotes these numbers and no others
    digest = hashlib.sha256(body).hexdigest()
    if f"release-report.json sha256:{digest}" not in page:
        found.append(
            f"{page_path.name} is not bound to {json_path.name} (sha256:{digest[:16]}…) — "
            "one of the two is from a different run"
        )

    # 4 and 5. the end-to-end suite, complete, on the lane being claimed
    attested = str(attestation.get("source", "<none>"))
    print(f"the end-to-end suite ran against: {attested}")
    if unbindable(attested):
        found.append(f"the e2e attestation is not bound to committed code ({attested})")
    elif attested != source:
        found.append(f"the e2e suite ran against {attested}, this release is {source}")

    run, total = attestation.get("checks_run"), attestation.get("checks_total")
    if run != total or not total:
        found.append(f"the e2e suite was partial: {run} of {total} checks")

    lane = str(attestation.get("lane", ""))
    print(f"the end-to-end lane was: {lane or '<none>'}")
    if not lane.startswith(RELEASE_LANES):
        found.append(
            f"the e2e suite ran on a lane that cannot carry a release claim: "
            f"{lane or '<none>'} (expected one of {', '.join(RELEASE_LANES)})"
        )

    # Which Ollama, and which bytes behind each tag. The models run on the
    # releaser's own machine now, so "it passed against qwen3.5:9b" is a claim
    # about a host nobody else can inspect — the version and the digests are what
    # make it checkable afterwards.
    missing_facts = [key for key in REQUIRED_MODEL_FACTS if not attestation.get(key)]
    if missing_facts:
        found.append(
            f"the e2e attestation does not say which model actually ran: "
            f"missing {', '.join(missing_facts)} — re-attest with a current verify-e2e.sh"
        )
    else:
        digests = attestation["model_digests"]
        print(f"ollama {attestation['ollama_version']}, models: {digests}")

    if commit and attestation.get("commit") not in (commit, None):
        found.append(f"the e2e suite ran at commit {attestation['commit']}, the tag is {commit}")

    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="what this checkout answers to")
    parser.add_argument("--commit", help="the commit being tagged, when there is one")
    parser.add_argument(
        "--evidence",
        type=Path,
        default=EVIDENCE,
        help="where the three artifacts live (overridable so this script can be tested)",
    )
    parser.add_argument(
        "--warn-only",
        action="store_true",
        help="report without failing — for rehearsals, which have no fresh measurement",
    )
    args = parser.parse_args(argv)

    print(f"this source answers to: {args.source}")
    found = problems(args.source, args.commit, args.evidence)
    if not found:
        print("release evidence agrees with the source being published")
        return 0

    for problem in found:
        message = f"refusing to publish — {problem}"
        print(f"::warning::rehearsal only, a tag would refuse: {problem}" if args.warn_only
              else f"error: {message}", file=sys.stderr)
    if args.warn_only:
        return 0
    print(
        "\nRun the full-fidelity lane against this exact tree and commit its output:\n"
        "  ./src/verify-e2e.sh --reset --attest release/evidence/e2e-attestation.json\n"
        "  cd src/workshops/assistant/after && make release-evidence\n"
        "  cp evidence/RELEASE-EVIDENCE.md evidence/release-report.json "
        "../../../../release/evidence/\n"
        "A 'dirty-' or 'unbound' id means the measurement was not taken against\n"
        "committed code; see docs/RELEASE-CHECKLIST.md step 5.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
