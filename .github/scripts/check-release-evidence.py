#!/usr/bin/env python3
"""Refuse to publish a release whose evidence is about something else.

    python3 .github/scripts/check-release-evidence.py --source "$(...)" [--inputs ID]

Three artifacts are committed by hand because the measurement needs a GPU and a
hosted runner has none: `release-report.json` (the numbers), `RELEASE-EVIDENCE.md`
(the page quoting them) and `e2e-attestation.json` (proof the deployed stack passed
its end-to-end suite). Hand-carried evidence is only worth anything if something
checks that it describes *this* source, so this does, in six ways:

  1. the report is bound to the source being published, and that binding is a real
     one — `dirty-` and `unbound` are refusals, not values, and they compare equal
     to each other, so they are rejected before any comparison — and it was measured
     from empty state rather than on top of an earlier run's writes, and it carries
     the containment property rather than one integer summarising it;
  2. `gate.py`'s four thresholds — quality, safety, latency, cost — reapplied over
     the committed numbers. Imported from the lesson rather than restated here: a
     second copy of a threshold is a threshold that will disagree with itself;
  3. the page is stapled to the JSON by digest, so a page quoting an older run
     cannot ride along with fresher numbers;
  4. the end-to-end suite ran to completion — every check, none skipped — and it
     FINISHED on the tier it claims, which is a different question: the tier checks
     run at the top and two later checks deliberately break the stack;
  5. it ran on the lane the release claims, not the fast CI overlay;
  6. it ran over the same release INPUTS being published — the workbook and the
     compose stack as well as the measured capstone.

Both bindings are tree object ids over paths that exclude `release/evidence/`,
which is what makes them checkable at all. The version of this script that
compared commit shas was unsatisfiable: an attestation names the commit it ran at,
committing it produces a new commit, and the gate then demanded the file predict
its own child. Publication could never pass, and the numbers were never the
problem.

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

#: What the stack has to still be when the suite finishes, not only when it starts.
#: Same five values `verify-e2e.sh` asserts in its closing check, restated here
#: because this script is what a release runs and it must not depend on the verifier
#: having been the current one. Five rather than all of them: these are the tiers a
#: release claim is about — which brain composed, which store retrieved, how, over
#: which embedder, and whether the outbound gate screened before releasing.
REQUIRED_FINAL_TIERS = {
    "brain": "ollama",
    "rag": "qdrant",
    "retrieval": "hybrid-rrf",
    "embed": "nomic-embed-text",
    "stream": "safe-buffered",
}

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


def problems(source: str, inputs: str | None, evidence: Path = EVIDENCE) -> list[str]:
    found: list[str] = []
    if unbindable(source):
        return [f"this checkout has no bindable source id ({source})"]
    if inputs is not None and unbindable(inputs):
        return [f"this checkout has no bindable release-inputs id ({inputs})"]

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

    # 1b. and they were measured from empty state. `--reuse-state` exists for
    # diagnosis and stamps the report so the diagnosis cannot become the release: a
    # run over a database holding earlier audit rows, memories and approvals has a
    # warm cache in its percentiles and other subjects in its recall.
    state = str(data.get("versions", {}).get("state", "<none>"))
    print(f"the state it was measured from: {state}")
    if state != "fresh":
        found.append(
            f"the numbers were measured from {state!r} state, not 'fresh' — rerun "
            "`make release-evidence` without --reuse-state"
        )

    # 1c. and what KIND of evidence they are. Printed, never gated: the value is a
    # qualification on how far the numbers can be quoted, not a threshold, and a gate
    # that rejected `smoke` would reject every release this lane can currently
    # produce. It is here because the audit's finding was that a reader of the gate
    # log saw a real judge, a real vector store and 58 red-team rows, and nothing
    # anywhere told them the eval suite was five rows over two slices.
    print(f"evidence class: {data.get('evidence_class', '<none>')} "
          "(see 'What this does not prove' on the page)")

    # 1d. and the containment property is IN the file. `gate.py` skips its
    # containment rules when `safety` is absent, because the offline lane cannot
    # measure them — three inline probes, no benign controls. That absence is fine on
    # a push and not fine here: release-class evidence claims a red team ran, and a
    # release whose report carries one integer would let every rule below it pass by
    # having nothing to check. So the requirement lives where the claim is made.
    if data.get("safety") is None:
        found.append(
            "the committed numbers carry no `safety` object, so the containment rules "
            "have nothing to check — re-measure with a current `make release-evidence`"
        )

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

    # 4b. and the stack it finished on is the stack it claims. `checks_run == total`
    # says every check passed; it does not say they passed against one tier. Checks 2
    # and 4 are the tier assertions and they run eleven checks before the file is
    # written, two of those eleven deliberately break the stack, and one restarts the
    # service — which clears the degradation map. So the closing read is required
    # here, and a missing field is a refusal rather than a skip: an attestation from
    # before this existed cannot answer the question, and "cannot answer" is the
    # state the field was added to make visible.
    final = attestation.get("final_tier")
    if not isinstance(final, dict) or not final.get("tier"):
        found.append(
            "the e2e attestation carries no closing tier snapshot (final_tier) — "
            "re-attest with a current verify-e2e.sh"
        )
    else:
        tiers, degraded = final["tier"], final.get("degraded") or {}
        print(f"the tier it finished on: {tiers.get('brain')} brain, "
              f"{tiers.get('rag')} rag, degraded: {degraded or 'nothing'}")
        if degraded:
            found.append(
                f"the e2e run finished with components degraded: {sorted(degraded)} — "
                "the suite passed on a stack it did not start on"
            )
        for key, expected in REQUIRED_FINAL_TIERS.items():
            if tiers.get(key) != expected:
                found.append(
                    f"the e2e run finished with tier.{key}={tiers.get(key)!r}, "
                    f"not {expected!r} — those numbers are not about the shipped tier"
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

    # 6. and the run covers every input this release is made of, not just the
    # measured ones. `source` above binds the capstone and the red-team dataset;
    # this binds the workbook, the compose stack and the verifier too.
    #
    # This replaced a comparison of commit shas, which could not be satisfied by any
    # honest release. The run recorded the commit it measured, committing that record
    # produced a different commit, and the tag gate then asked the record to name a
    # commit that did not exist when it was written. Every numeric gate passed and
    # publication exited 1, permanently. Tree ids over paths that exclude
    # `release/evidence/` make the same claim as a fixed point: committing the
    # evidence cannot change what the evidence is bound to.
    if inputs is not None:
        attested_inputs = str(attestation.get("inputs") or "<none>")
        print(f"the release inputs it ran over: {attested_inputs}")
        # An attestation from before this field existed is missing it rather than
        # disagreeing, and the two want different sentences: one says re-attest,
        # the other says you measured the wrong tree.
        if attested_inputs == "<none>" or unbindable(attested_inputs):
            found.append(
                f"the e2e attestation carries no release-inputs binding ({attested_inputs}) "
                "— re-attest with a current verify-e2e.sh"
            )
        elif attested_inputs != inputs:
            found.append(
                f"the e2e suite ran over release inputs {attested_inputs}, "
                f"this release is {inputs}"
            )

    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="what this checkout answers to")
    parser.add_argument("--inputs", help="the release-inputs id this checkout answers to")
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
    if args.inputs:
        print(f"these release inputs answer to: {args.inputs}")
    found = problems(args.source, args.inputs, args.evidence)
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
