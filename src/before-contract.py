#!/usr/bin/env python3
"""Is this before/ scaffold red for the RIGHT reason?

`verify-lessons.sh --before` used to accept any nonzero pytest exit as "failing by
design":

    if uv run pytest -q -m "not integration" >/dev/null 2>&1; then
      echo "TESTS-PASS-UNEXPECTEDLY"; exit 1
    fi

Which makes a broken scaffold indistinguishable from a working one. A missing
import, a syntax error, a renamed module, a plugin that will not load, a conftest
that raises, an empty test suite — every one of those exits nonzero and reported
OK. The check said "the tests fail", which was true, and implied "and a student
can make them pass", which is a different claim.

So: run collection first, and hold the failures to a contract.

    python3 before-contract.py results.xml

Reads a JUnit XML report (pytest writes one with `--junit-xml`, no plugin needed)
and prints one reason token on stdout, or nothing when the scaffold is sound. The
token goes straight into `verify-lessons.sh`'s FAIL line.

Stdlib only, and fast — it parses a file that the test run already produced.
"""
from __future__ import annotations

import collections
import re
import sys
import xml.etree.ElementTree as ET

#: Exceptions that mean "the student has not written this yet".
#:
#: Not a guess: this is what the 34 before/ trees actually raise, surveyed before
#: the rule was written. `NotImplementedError` is the stub bodies and dominates by
#: two orders of magnitude. `AssertionError` is a test asserting on behaviour that
#: does not exist yet, and `Failed` is the same thing via `pytest.fail`.
#:
#: `KeyError` and `IndexError` are here on purpose and are the interesting pair. A
#: scaffold whose exercise is to POPULATE A TABLE — `PROVIDERS` in
#: phase1-foundations/01, the tool registry in the capstone — raises `KeyError`
#: when a test asks for a row, and that is the scaffold working. The alternative is
#: wrapping dict literals in functions that raise `NotImplementedError`, which is
#: worse code written to satisfy a gate. The cost of allowing them is that a
#: genuine typo'd key reads as intended incompleteness, which is why the rule below
#: also requires at least one failure from the first three.
INCOMPLETE = frozenset({
    "NotImplementedError",
    "AssertionError",
    "Failed",
    "KeyError",
    "IndexError",
})

#: Of those, the ones that can only be deliberate. A scaffold failing exclusively
#: on the collection-shaped errors above is more likely broken than designed.
BY_DESIGN = frozenset({"NotImplementedError", "AssertionError", "Failed"})

#: pytest writes a failure's message as `Type: detail` and a setup error's as
#: `failed on setup with "Type: detail"`. Both start the type at a word boundary
#: after an optional module path, which is what this pulls out.
#:
#: The XML has no `type` attribute to read instead — checked, on a real report;
#: pytest's JUnit writer emits `message` and nothing else.
TYPE_RE = re.compile(r'(?:failed on \w+ with ")?(?:[\w.]+\.)?(\w+(?:Error|Exception)|Failed)')

#: A plain `assert x == y` in a test does not produce a `AssertionError:` prefix.
#: pytest rewrites the statement and the message it reports is the rewritten
#: expression — `assert 3 == 1\n + where 3 = ...`. That is the most ordinary
#: failure a test can have, and reading it as "unrecognised" would flag the
#: healthiest scaffolds in the tree. Two of them, on the first run.
REWRITTEN_ASSERT = re.compile(r"^assert\b")

#: pytest messages that carry no exception at all, so the traceback has to be read.
GENERIC_MESSAGES = frozenset({"collection failure", "internal error"})


def exception_types(report: ET.Element) -> collections.Counter[str]:
    """Every failure and setup error in the report, counted by exception type.

    Setup errors count. All 37 of the capstone's are `NotImplementedError` raised
    by a stub a fixture happened to call, so treating an error as automatically
    disqualifying would fail a scaffold for where its stub sits rather than for
    what it does.
    """
    found: collections.Counter[str] = collections.Counter()
    for case in report.iter("testcase"):
        for bad in (*case.findall("failure"), *case.findall("error")):
            found[type_of(bad.get("message", ""), bad.text or "")] += 1
    return found


def type_of(message: str, body: str = "") -> str:
    """The exception behind one failure, or "unrecognised"."""
    if REWRITTEN_ASSERT.match(message):
        return "AssertionError"
    # A module that will not import gets the flat message "collection failure" and
    # keeps the exception in the traceback. Reporting that as unrecognised would
    # name the one failure mode this file was added for the least usefully of all,
    # so the body answers when the message declines to.
    if message.strip() in GENERIC_MESSAGES:
        match = TYPE_RE.search(body)
        return match.group(1) if match else "unrecognised"
    match = TYPE_RE.match(message)
    return match.group(1) if match else "unrecognised"


def verdict(report: ET.Element) -> str:
    """A reason token, or "" when the scaffold is red for the right reason."""
    cases = [c for c in report.iter("testcase")]
    if not cases:
        return "NO-TESTS"

    found = exception_types(report)
    if not found:
        return "TESTS-PASS-UNEXPECTEDLY"

    # Named rather than counted: "BROKEN-ImportError" tells a maintainer what to
    # open. A bare count would send them back to pytest to find out.
    unexpected = sorted(set(found) - INCOMPLETE)
    if unexpected:
        return "BROKEN-" + ",".join(unexpected)

    if not (set(found) & BY_DESIGN):
        return "NOT-RED-BY-DESIGN-" + ",".join(sorted(found))
    return ""


#: Each rule shown failing on the mistake it exists to catch, and passing on the
#: fix. The whole point of this file is to say no to reports the old check said yes
#: to, and a rule nobody has seen red is a rule nobody has tested. Run with
#: `--selftest`; CI does.
SELFTEST: list[tuple[str, str, str]] = [
    (
        "a stub-driven scaffold is what a before/ tree should look like",
        '<testsuite><testcase name="a"><failure message="NotImplementedError"/></testcase></testsuite>',
        "",
    ),
    (
        "a rewritten assert is an AssertionError, not an unknown exception",
        '<testsuite><testcase name="a">'
        '<failure message="assert 3 == 1&#10; +  where 3 = obj.calls"/></testcase></testsuite>',
        "",
    ),
    (
        "a setup error counts, and its exception is what decides",
        '<testsuite><testcase name="a">'
        '<error message="failed on setup with &quot;NotImplementedError: write() is yours&quot;"/>'
        "</testcase></testsuite>",
        "",
    ),
    (
        "a scaffold that does not import is the failure the old check waved through",
        '<testsuite><testcase name="a">'
        '<error message="failed on setup with &quot;ModuleNotFoundError: no module named assistant&quot;"/>'
        "</testcase></testsuite>",
        "BROKEN-ModuleNotFoundError",
    ),
    (
        "so is a scaffold whose stub returns None and trips a TypeError downstream",
        '<testsuite><testcase name="a"><failure message="TypeError: not subscriptable"/></testcase>'
        '<testcase name="b"><failure message="NotImplementedError"/></testcase></testsuite>',
        "BROKEN-TypeError",
    ),
    (
        "an empty suite exits nonzero and used to read as red by design",
        "<testsuite/>",
        "NO-TESTS",
    ),
    (
        "a scaffold a student has already finished is not a scaffold",
        '<testsuite><testcase name="a"/><testcase name="b"/></testsuite>',
        "TESTS-PASS-UNEXPECTEDLY",
    ),
    (
        "a table the student fills raises KeyError, which is allowed alongside a stub",
        '<testsuite><testcase name="a"><failure message="KeyError: \'gpt\'"/></testcase>'
        '<testcase name="b"><failure message="NotImplementedError"/></testcase></testsuite>',
        "",
    ),
    (
        "but KeyError alone is more likely a typo than a lesson",
        '<testsuite><testcase name="a"><failure message="KeyError: \'gpt\'"/></testcase></testsuite>',
        "NOT-RED-BY-DESIGN-KeyError",
    ),
    (
        "a module that will not import names the exception, not 'collection failure'",
        '<testsuite><testcase name="a"><error message="collection failure">'
        "ImportError while importing test module &apos;tests/test_x.py&apos;."
        "</error></testcase></testsuite>",
        "BROKEN-ImportError",
    ),
    (
        "a dotted exception path resolves to its type",
        '<testsuite><testcase name="a">'
        '<failure message="_pytest.outcomes.Failed: needs a real model"/></testcase></testsuite>',
        "",
    ),
]


def selftest() -> int:
    bad = 0
    for name, xml, want in SELFTEST:
        got = verdict(ET.fromstring(xml))
        if got == want:
            continue
        bad += 1
        print(f"  {name}\n    wanted {want!r}, got {got!r}")
    print(f"before-contract selftest: {len(SELFTEST) - bad}/{len(SELFTEST)} rules behave")
    return 1 if bad else 0


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[1] == "--selftest":
        return selftest()
    if len(argv) != 2:
        print("usage: before-contract.py RESULTS.xml | --selftest", file=sys.stderr)
        return 2
    try:
        report = ET.parse(argv[1]).getroot()
    except (OSError, ET.ParseError):
        # The report is written by the run being judged, so an unreadable one is a
        # finding rather than a crash: pytest died before it could write.
        print("NO-REPORT")
        return 1
    reason = verdict(report)
    if reason:
        print(reason)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
