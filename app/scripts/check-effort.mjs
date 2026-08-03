#!/usr/bin/env node
/**
 * The nine workshop estimates are answerable to the source they estimate.
 *
 * `check-integrity` already forces each workbook figure to match the `**Effort.**`
 * line in its brief, so the number a learner reads cannot drift from the number the
 * brief claims. Neither was anchored to anything: both could be wrong together, and
 * were — nine numbers from five guesses, every `realistic` exactly twice its `fast`.
 *
 * These are author's estimates and this gate does not pretend otherwise. What it
 * enforces is the three things that separate an estimate from a guess:
 *
 *   1. **Bounded.** Each `fast` sits inside the range the measured proxies span.
 *      Rewrite a brief or gut a suite and the bound moves; if it moves out from under
 *      the number, this fails. See `lib/effort.mjs` for what is measured and why each
 *      proxy is wrong in a nameable direction.
 *   2. **Not a formula.** The nine `realistic / fast` ratios cannot collapse to one
 *      value. That collapse is the exact tell this work removed.
 *   3. **Labelled.** Every brief carries the provenance line, in the same words, so a
 *      learner planning a weekend knows these were estimated rather than timed.
 *
 *   node scripts/check-effort.mjs            # gate
 *   node scripts/check-effort.mjs --report   # the evidence table, and no verdict
 *
 * Lessons are out of scope: their estimates are what the rates in `lib/effort.mjs`
 * were back-solved FROM, so checking them against a bound calibrated on them would be
 * a tautology with a passing exit code.
 */
import { readdirSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { assess, PROVENANCE_NOTE, WORKSHOPS } from "./lib/effort.mjs";

const repo = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const report = process.argv.includes("--report");

const read = {
  file(path) {
    try {
      return readFileSync(resolve(repo, path), "utf8");
    } catch {
      return null;
    }
  },
  list(path) {
    try {
      return readdirSync(resolve(repo, path)).filter((f) => f.endsWith(".py"));
    } catch {
      return [];
    }
  },
};

/** The declared figures, read out of the workbook's phase data. */
function declared() {
  const found = new Map();
  const dir = resolve(repo, "app/src/data/phases");
  for (const file of readdirSync(dir).filter((f) => f.endsWith(".ts"))) {
    const source = readFileSync(resolve(dir, file), "utf8");
    const pattern =
      /id: "([\w-]+)",[\s\S]{0,600}?effort: \{ fast: (\d+), integration: (\d+|null), realistic: (\d+) \}/g;
    for (const [, id, fast, integration, realistic] of source.matchAll(pattern)) {
      if (!(id in WORKSHOPS) || found.has(id)) continue;
      found.set(id, {
        file: `app/src/data/phases/${file}`,
        fast: Number(fast),
        integration: integration === "null" ? null : Number(integration),
        realistic: Number(realistic),
      });
    }
  }
  return found;
}

const declarations = declared();
const findings = [];
const rows = [];

for (const [id, workshop] of Object.entries(WORKSHOPS)) {
  const want = assess(read, id, workshop);
  rows.push({ id, want });

  // 1. bounded by the evidence
  if (!want.bound) {
    findings.push(`${id}: no proxy returned a number, so nothing bounds this estimate`);
  } else if (!want.inBound) {
    findings.push(
      `${id}: fast is ${want.fast} min, outside the ${Math.round(want.bound.low)}-${Math.round(
        want.bound.high,
      )} min the proxies span.\n` +
        `    proxies: ${JSON.stringify(want.minutes)} · counts: ${JSON.stringify(want.counts)}`,
    );
  }

  // 2. the workbook says what lib/effort.mjs says
  const got = declarations.get(id);
  if (!got) {
    findings.push(`${id}: no effort estimate in the workbook, so nothing shows on the card`);
  } else {
    for (const key of ["fast", "realistic"]) {
      if (got[key] !== want[key]) {
        findings.push(
          `${id} (${got.file}): ${key} is ${got[key]}, but ESTIMATES says ${want[key]}`,
        );
      }
    }
    if (got.integration !== (workshop.integrationMin ?? null)) {
      findings.push(
        `${id} (${got.file}): integration is ${got.integration}, but WORKSHOPS records ${workshop.integrationMin}`,
      );
    }
  }

  // 3. the brief carries the provenance line
  const brief = read.file(`src/${workshop.repo}/${workshop.brief}`);
  if (brief === null) {
    findings.push(`${id}: ${workshop.brief} does not exist`);
  } else if (!brief.includes(PROVENANCE_NOTE)) {
    findings.push(
      `${id}: ${workshop.brief} does not carry the provenance line. Add it under **Effort.**:\n` +
        `    ${PROVENANCE_NOTE}`,
    );
  }
}

// 4. not a formula
const ratios = new Set(rows.map(({ want }) => (want.realistic / want.fast).toFixed(2)));
if (ratios.size < 3) {
  findings.push(
    `every workshop's realistic/fast collapsed to ${[...ratios].join(", ")}. That ratio ` +
      `being constant is what made the old numbers a formula rather than nine estimates.`,
  );
}

if (report) {
  const pad = (v, n) => String(v).padStart(n);
  console.log(
    "workshop      groups tests deliv words │ todos tests deliv │  envelope  │ fast integ real ratio",
  );
  for (const { id, want } of rows) {
    const { groups, tests, deliverables, words } = want.counts;
    const m = want.minutes;
    const b = want.bound
      ? `${pad(Math.round(want.bound.low), 4)}-${pad(Math.round(want.bound.high), 5)}`
      : "    —    ";
    console.log(
      `${id.padEnd(13)} ${pad(groups, 6)} ${pad(tests, 5)} ${pad(deliverables, 5)} ${pad(words, 5)} │ ` +
        `${pad(Math.round(m.todos), 5)} ${pad(Math.round(m.tests), 5)} ${pad(Math.round(m.deliverables), 5)} │ ` +
        `${b} │ ${pad(want.fast, 4)} ${pad(want.integration ?? "—", 5)} ${pad(want.realistic, 4)} ` +
        `${(want.realistic / want.fast).toFixed(2)}`,
    );
  }
  process.exit(0);
}

if (findings.length) {
  console.error(`Effort: ${findings.length} problem(s) with the workshop estimates.\n`);
  for (const finding of findings) console.error(`  - ${finding}`);
  console.error(
    "\n  `node scripts/check-effort.mjs --report` prints the evidence. An estimate that\n" +
      "  left its envelope is either a number to revisit or a brief that changed shape —\n" +
      "  decide which, and record the reasoning in ESTIMATES[id].why rather than only\n" +
      "  moving the digit.",
  );
  process.exit(1);
}

console.log(
  `Effort OK — ${rows.length} workshop estimates inside their evidence envelopes, ` +
    `${ratios.size} distinct realistic/fast ratios, every brief labelled.`,
);
