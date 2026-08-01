#!/usr/bin/env node
/**
 * Proves the rebuilt source still carries the exact content of the shipped
 * bundle: bundles `src/data/` with esbuild, imports it, and deep-compares every
 * phase against the data recovered from the reference HTML.
 *
 *   node scripts/check-parity.mjs --bundle path/to/course.html
 *
 * `--bundle` is required and has no default: the repo keeps no reference bundle,
 * since course.html is a build output. Point it at an archived original.
 *
 * Phases added after the reconstruction are reported as new, not as failures;
 * only the seven original phases must match byte for byte.
 *
 * **Its window has closed.** The reconstruction was proved character-for-character
 * on 2026-07-31, and content has intentionally moved on since (Phase 2's
 * scorekeeping card was rewritten when Phase 3 landed, every objective was
 * rewritten for Bloom verbs, phases were renumbered twice). Against the original
 * bundle it now reports ~100 differences, all of them deliberate. Kept because it
 * is the only tool that can re-prove a recovery from a bundle, and because
 * `lib/bundle-data.mjs` only parses the original minified format. For ongoing
 * safety use `check-alignment.mjs`, which gates the build.
 */
import path from "node:path";
import process from "node:process";
import { readBundleData } from "./lib/bundle-data.mjs";
import { appRoot, loadCourseData } from "./lib/load-data.mjs";

const args = process.argv.slice(2);
const argOf = (flag, fallback) => {
  const i = args.indexOf(flag);
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback;
};
const bundleArg = argOf("--bundle", null);
if (!bundleArg) {
  console.error("usage: node scripts/check-parity.mjs --bundle path/to/course.html");
  console.error("       needs an original minified bundle; a current build will not parse.");
  process.exit(2);
}
const bundlePath = path.resolve(appRoot, bundleArg);

const problems = [];
const notes = [];

function compare(pathLabel, expected, actual) {
  if (
    typeof expected === "string" ||
    typeof expected === "number" ||
    typeof expected === "boolean"
  ) {
    if (expected !== actual) {
      problems.push(
        `${pathLabel}\n    bundle: ${JSON.stringify(expected)}\n    source: ${JSON.stringify(actual)}`,
      );
    }
    return;
  }
  if (Array.isArray(expected)) {
    if (!Array.isArray(actual)) {
      problems.push(`${pathLabel}: expected an array, source has ${typeof actual}`);
      return;
    }
    if (expected.length !== actual.length) {
      problems.push(
        `${pathLabel}: bundle has ${expected.length} items, source has ${actual.length}`,
      );
    }
    for (const [i, item] of expected.entries()) {
      compare(`${pathLabel}[${i}]`, item, actual[i]);
    }
    return;
  }
  if (expected && typeof expected === "object") {
    if (!actual || typeof actual !== "object") {
      problems.push(`${pathLabel}: expected an object, source has ${typeof actual}`);
      return;
    }
    for (const [key, value] of Object.entries(expected)) {
      compare(`${pathLabel}.${key}`, value, actual[key]);
    }
    const extra = Object.keys(actual).filter((k) => !(k in expected) && k !== "num");
    if (extra.length) notes.push(`${pathLabel}: source adds ${extra.join(", ")}`);
    return;
  }
  if (expected !== actual) problems.push(`${pathLabel}: ${expected} !== ${actual}`);
}

const bundleData = readBundleData(bundlePath);
const source = await loadCourseData();

compare("prerequisites", bundleData.prereqs, source.prerequisites);
compare("myths", bundleData.myths, source.myths);
compare("milestones", bundleData.milestones, source.milestones);

for (const bundlePhase of bundleData.phases) {
  const sourcePhase = source.phases.find((p) => p.id === bundlePhase.id);
  if (!sourcePhase) {
    problems.push(`phase ${bundlePhase.id} is missing from the source`);
    continue;
  }
  // `num` is derived from course order, so a renumbering is expected, not a drift.
  const { num: bundleNum, ...content } = bundlePhase;
  if (bundleNum !== sourcePhase.num) {
    notes.push(`phase ${bundlePhase.id}: renumbered ${bundleNum} -> ${sourcePhase.num}`);
  }
  compare(`phase ${bundlePhase.id}`, content, sourcePhase);
}

const added = source.phases.filter((p) => !bundleData.phases.some((b) => b.id === p.id));
for (const phase of added) notes.push(`phase ${phase.id} (${phase.title}) is new since the bundle`);

console.log(`Reference bundle: ${path.relative(process.cwd(), bundlePath)}`);
console.log(
  `Compared ${bundleData.phases.length} phases · ${bundleData.prereqs.length} prerequisites · ` +
    `${bundleData.myths.length} myths · ${bundleData.milestones.length} milestones`,
);
for (const note of notes) console.log(`  note: ${note}`);

if (problems.length) {
  console.error(`\n${problems.length} content difference(s):`);
  for (const problem of problems.slice(0, 40)) console.error(`  - ${problem}`);
  if (problems.length > 40) console.error(`  ... and ${problems.length - 40} more`);
  process.exit(1);
}

console.log("\nContent parity OK — the source carries the shipped content exactly.");
