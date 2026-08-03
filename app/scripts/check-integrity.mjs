#!/usr/bin/env node
/**
 * Data-integrity gate: id collisions, id prefixes, block kinds, table shapes,
 * empty content, resource urls and repo paths.
 *
 * The third gate, and the one that catches the boring failures the other two are
 * not looking for. Alignment can pass on a phase whose resource links are all
 * typos; density can pass on a table missing a column. Neither breaks a build, and
 * both are found by a student rather than by us.
 *
 * It also covers ground the alignment gate structurally could not: that walk only
 * ever visited the phase spine it needed for the teaches/assesses graph, so the
 * q-bank, the prerequisites and the four electives were never checked for id
 * collisions at all — despite ids being the localStorage progress keys.
 *
 *   node scripts/check-integrity.mjs            # gate: exits 1 on any violation
 *   node scripts/check-integrity.mjs --report   # also print what was walked
 *
 * The rules live in `lib/integrity.mjs` and are unit-tested in `integrity.test.mjs`.
 */
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { audit } from "./lib/integrity.mjs";
import { appRoot, loadCourseData } from "./lib/load-data.mjs";

const srcRoot = path.resolve(appRoot, "../src");

/** What the lesson README or workshop brief itself claims, or null if there is no such file. */
function effortLineOf(relative) {
  const file = path.join(srcRoot, relative);
  if (!fs.existsSync(file)) return null;
  return fs.readFileSync(file, "utf8").match(/^\*\*Effort\.\*\*.*$/m)?.[0] ?? "";
}

const { phases, prerequisites, electives } = await loadCourseData();
const { errors, counts } = audit({
  phases,
  prerequisites,
  electives,
  repoExists: (repo) => fs.existsSync(path.join(srcRoot, repo)),
  effortLineOf,
});

console.log(
  `Integrity scan · ${counts.ids} ids · ${counts.blocks} blocks · ` +
    `${counts.resources} resources · ${counts.electives} electives · ` +
    `${counts.defenses} defended checkpoints · ` +
    `${counts.efforts} effort estimates matched to their lesson`,
);

if (process.argv.includes("--report")) {
  for (const phase of phases) {
    const repos = [...phase.exercises, ...(phase.workshop ? [phase.workshop] : [])]
      .map((task) => task.repo)
      .filter(Boolean);
    console.log(
      `\n  Phase ${phase.num} · ${phase.title}` +
        `\n    ${phase.concepts.length} cards · ${phase.resources.length} resources · ${repos.length} repo paths`,
    );
    for (const repo of repos) console.log(`      src/${repo}`);
  }
  console.log("");
}

if (errors.length) {
  console.error(`\n${errors.length} integrity problem(s):`);
  for (const e of errors) console.error(`  - [${e.rule}] ${e.subject}: ${e.message}`);
  process.exit(1);
}
console.log(
  "\nIntegrity OK — ids are unique, links are links, tables are rectangles, and " +
    "every phase asks for all four halves of a design answer.",
);
