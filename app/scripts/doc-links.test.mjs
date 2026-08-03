import assert from "node:assert/strict";
import test from "node:test";
import { PRODUCED, producedFindings, referenceFindings, referencesIn } from "./lib/doc-links.mjs";

/**
 * A miniature of the real layout: a capstone with a run root, a checklist under
 * it, a workshop-level document one directory above, and a lesson pair.
 */
const SHIPPED = new Set([
  "src/README.md",
  "src/workshops/assistant/ARCHITECTURE.md",
  "src/workshops/assistant/README.md",
  "src/workshops/assistant/after/Makefile",
  "src/workshops/assistant/after/pyproject.toml",
  "src/workshops/assistant/after/docs/RELEASE-CHECKLIST.md",
  "src/workshops/assistant/after/src/assistant/release.py",
  "src/phase7-mcp/SDK-V2-MIGRATION.md",
  "src/phase7-mcp/01-consume-a-server/after/README.md",
  "src/phase7-mcp/01-consume-a-server/after/pyproject.toml",
  "src/phase1-foundations/VERIFIED.md",
]);

const findings = (file, source, shipped = SHIPPED) =>
  referenceFindings([{ file, source }], shipped);

test("a path that resolves from the file's own directory passes", () => {
  const at = "src/workshops/assistant/README.md";
  assert.deepEqual(findings(at, "see [the checklist](after/docs/RELEASE-CHECKLIST.md)"), []);
});

test("a path written from src/ passes, because src/ is the zip's root", () => {
  const at = "src/phase7-mcp/01-consume-a-server/after/README.md";
  const source = "`workshops/assistant/after/docs/RELEASE-CHECKLIST.md` makes it a precondition";
  assert.deepEqual(findings(at, source), []);
});

test("a path in a program resolves from where the program runs, not where it lives", () => {
  // The exact shape of `release.py`'s failure message. The file is three
  // directories below the run root; the student who reads the message is at the
  // run root, because that is where `make evidence` is typed.
  const at = "src/workshops/assistant/after/src/assistant/release.py";
  assert.deepEqual(findings(at, '"ASSISTANT_DB. See docs/RELEASE-CHECKLIST.md."'), []);
});

test("the run root is found through a Makefile as well as a pyproject", () => {
  const shipped = new Set([...SHIPPED].filter((p) => !p.endsWith("after/pyproject.toml")));
  const at = "src/workshops/assistant/after/src/assistant/release.py";
  assert.deepEqual(findings(at, "See docs/RELEASE-CHECKLIST.md.", shipped), []);
});

test("the original bug: an untracked checklist fails every reference to it", () => {
  // Precisely the pre-fix tree — the file on disk, ignored by a bare `docs/`
  // rule, so absent from `git ls-files` and therefore from the zip.
  const unshipped = new Set([...SHIPPED].filter((p) => !p.endsWith("docs/RELEASE-CHECKLIST.md")));
  const at = "src/workshops/assistant/after/src/assistant/release.py";
  const [finding] = findings(at, "See docs/RELEASE-CHECKLIST.md.", unshipped);
  assert.equal(finding.rule, "doc-link");
  assert.match(finding.message, /does not reach the zip/);
  assert.match(finding.message, /untracked/);
});

test("a link one `..` short of its target is caught", () => {
  // Three phase-7 READMEs shipped this: `../SDK-V2-MIGRATION.md` from an
  // `after/` directory climbs to the lesson, not to the phase.
  const at = "src/phase7-mcp/01-consume-a-server/after/README.md";
  const [finding] = findings(at, "see [`../SDK-V2-MIGRATION.md`](../SDK-V2-MIGRATION.md).");
  assert.equal(finding.rule, "doc-link");
  assert.match(finding.message, /SDK-V2-MIGRATION/);
  // And the corrected form passes, so the test pins the fix and not just the bug.
  assert.deepEqual(findings(at, "see [x](../../SDK-V2-MIGRATION.md)"), []);
});

test("a bare name in prose passes when something in the zip is called that", () => {
  const at = "src/workshops/assistant/after/src/assistant/report.py";
  // `ARCHITECTURE.md` sits at the workshop root, above the capstone — no
  // relative base reaches it, and the prose is naming a document rather than
  // routing to one.
  assert.deepEqual(findings(at, '"diagrams in `ARCHITECTURE.md`"'), []);
  // One name, eleven files: `VERIFIED.md` is a per-phase stamp.
  assert.deepEqual(findings("src/README.md", "a `VERIFIED.md` stamp saying when"), []);
});

test("a bare name nothing in the zip answers to is still caught", () => {
  const [finding] = findings("src/README.md", "see `RUNBOOK.md` for the incident steps");
  assert.equal(finding.rule, "doc-name");
  assert.match(finding.message, /no file in the zip is called that/);
});

test("an anchor is not part of the path", () => {
  const at = "src/README.md";
  const source = "[the twenty minutes](phase1-foundations/VERIFIED.md#the-twenty-minutes)";
  assert.deepEqual(findings(at, source), []);
});

test("references are deduplicated per file", () => {
  const source = "`ARCHITECTURE.md` and again `ARCHITECTURE.md` and [x](ARCHITECTURE.md)";
  assert.equal(referencesIn("src/workshops/assistant/README.md", source).length, 1);
});

test("what ends in .md and is not a document reference is left alone", () => {
  // Each of these is a real line from the tree, and each addresses something
  // that is not a file in this repo.
  const source = [
    'c.request("DELETE", "/corpus/r.md")', //           an HTTP route
    'as "$ALICE" -X DELETE "$BASE/corpus/priority.md"', // interpolated at run time
    "cp METRICS-WORKSHEET.md ~/job-search/metrics.md", // outside the checkout
    "the `workshops/assistant/WORKSHOP-*.md` set", //    a glob, not a path
    "see https://example.com/guide.md for more", //      somewhere else entirely
    'RELEASE_INPUTS = ("src", "app", "release/README.md")', // the bundle's namespace
    "#: `release/README.md` is named individually rather than taking `release/`",
  ].join("\n");
  // Nothing at all: the `cp` line contributes neither side — `~/job-search/...`
  // is outside the checkout, and the bare, unbackticked `METRICS-WORKSHEET.md`
  // is a shell argument rather than a citation, which is why only backticked
  // basenames are collected.
  //
  // The last two are `provenance.RELEASE_INPUTS`, which is a list of arguments to
  // `git rev-parse HEAD:<path>` and therefore repository paths by requirement. The
  // README it names ships beside the zip, next to `course.html` — so it is not
  // missing, it is in the bundle's namespace rather than the zip's, and rewriting the
  // constant to resolve here would break the digest it computes.
  assert.deepEqual(referencesIn("src/verify-e2e.sh", source), []);
});

test("a document the learner writes is not required to exist", () => {
  assert.ok(PRODUCED.has("PORTFOLIO.md"));
  const at = "src/workshops/assistant/README.md";
  assert.deepEqual(findings(at, "`make report` writes `PORTFOLIO.md` beside the code"), []);
});

test("PRODUCED cannot hold a name that actually ships", () => {
  const shipped = new Set([...SHIPPED, "src/workshops/assistant/after/PORTFOLIO.md"]);
  const files = [{ file: "src/README.md", source: "`PORTFOLIO.md`" }];
  const [finding] = producedFindings(files, shipped).filter((f) => f.subject === "PORTFOLIO.md");
  assert.match(finding.message, /tracked and shipped/);
});

test("PRODUCED cannot hold a name nothing mentions", () => {
  const files = [{ file: "src/README.md", source: "no documents named here" }];
  const stale = producedFindings(files, SHIPPED);
  assert.equal(stale.length, PRODUCED.size);
  assert.match(stale[0].message, /stale entry/);
});
