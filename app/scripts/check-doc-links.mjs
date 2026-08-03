#!/usr/bin/env node
/**
 * Packaging gate: every document `src/` points at is a document the zip carries.
 *
 *   node scripts/check-doc-links.mjs            # gate: exits 1 on a dangling reference
 *   node scripts/check-doc-links.mjs --report   # also list every reference and its target
 *
 * The oracle is git, not the filesystem. `package.sh` builds the companion zip
 * with `git archive HEAD -- src`, so a file that is untracked — or tracked
 * outside `src/` — does not reach a student no matter how present it looks in a
 * working copy. That is exactly how the capstone's `RELEASE-CHECKLIST.md` went
 * missing from every release while sitting in plain view of whoever wrote the
 * seven references to it.
 *
 * The index is read rather than `HEAD`, so a checklist staged for the commit
 * that fixes it counts as shipped. What the index cannot see is a *later*
 * `.gitignore` edit re-ignoring a tracked file; git keeps tracking it, so it
 * still ships, and the gate still agrees.
 *
 * Rules live in `lib/doc-links.mjs` and are unit-tested in `doc-links.test.mjs`.
 */
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { PRODUCED, producedFindings, referenceFindings, referencesIn } from "./lib/doc-links.mjs";

const repo = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const report = process.argv.includes("--report");

/**
 * Everything `git archive HEAD -- src` would carry, as repo-relative paths.
 *
 * Refuses rather than guesses when there is no checkout. Falling back to a
 * directory walk would answer a different question — "is the file on disk" — and
 * that question answered "yes" for the entire time the checklist was missing from
 * every release, which is what made the bug invisible.
 */
function shippedFiles() {
  let listed;
  try {
    listed = execFileSync("git", ["ls-files", "-z", "--", "src"], {
      cwd: repo,
      encoding: "utf8",
      maxBuffer: 32 * 1024 * 1024,
      stdio: ["ignore", "pipe", "pipe"],
    });
  } catch (cause) {
    console.error(
      "error: this gate needs a git checkout, and this is not one.\n" +
        "       Whether a document ships is decided by `git archive HEAD -- src`,\n" +
        "       so git is the only thing that can answer it — a directory walk would\n" +
        "       pass a file that is present on disk and absent from every release,\n" +
        "       which is the exact bug this gate exists for.\n" +
        `       (git said: ${String(cause.stderr ?? cause.message).trim()})`,
    );
    process.exit(1);
  }
  return new Set(listed.split("\0").filter(Boolean));
}

const shipped = shippedFiles();

/**
 * Text worth scanning, which is not the same as text worth *rendering*. The
 * Makefile comment and the Python error message that pointed at the missing
 * checklist are both references a student follows, so both are in scope.
 * Everything binary or generated is out.
 */
const SCANNED = /\.(md|py|toml|ya?ml|sh|txt|json|jsonl|ts|tsx|js|mjs|cfg|ini|Dockerfile)$/;
const SCANNED_EXACT = /(^|\/)(Makefile|Dockerfile|\.env\.example)$/;

const files = [];
for (const file of shipped) {
  if (!SCANNED.test(file) && !SCANNED_EXACT.test(file)) continue;
  files.push({ file, source: readFileSync(resolve(repo, file), "utf8") });
}

const findings = [...referenceFindings(files, shipped), ...producedFindings(files, shipped)];
const total = files.reduce((n, f) => n + referencesIn(f.file, f.source).length, 0);

console.log(
  `Doc links · ${files.length} scanned file(s) · ${total} reference(s) · ` +
    `${shipped.size} file(s) in the zip · ${PRODUCED.size} produced-at-runtime name(s)`,
);

if (report) {
  console.log("\n  Every reference and where it lands:");
  for (const { file, source } of files) {
    const refs = referencesIn(file, source);
    if (!refs.length) continue;
    console.log(`    ${file}`);
    for (const { path } of refs) console.log(`      -> ${path}`);
  }
}

if (findings.length) {
  console.log(`\n  ${findings.length} problem(s):`);
  for (const { rule, subject, message } of findings)
    console.log(`    [${rule}] ${subject} ${message}`);
  console.log(
    "\nA reference that does not resolve is a dead end for whoever follows it.\n" +
      "Fix the path, track the file, or — if the learner writes it — add the\n" +
      "basename to PRODUCED in scripts/lib/doc-links.mjs with the command that emits it.",
  );
  process.exit(1);
}

console.log("\nDoc links: OK — every referenced document ships.");
