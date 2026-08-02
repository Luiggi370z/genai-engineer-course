#!/usr/bin/env node
/**
 * Constructive-alignment gate.
 *
 * Constructive alignment means three things agree: what a phase claims to teach
 * (objectives), what it actually teaches (concept cards), and what it asks the
 * student to do (exercises, workshops). When they drift you get the classic
 * course defect — taught 1+1, tested 1×1 — and nothing notices, because nothing
 * in a content repo fails when prose stops matching practice.
 *
 * This fails. `pnpm build` runs it, so an unaligned exercise cannot reach a bundle.
 * Whether the data is *well-formed* is a separate question, asked next door by
 * `check-integrity.mjs`.
 *
 *   node scripts/check-alignment.mjs            # gate: exits 1 on any violation
 *   node scripts/check-alignment.mjs --report   # also print the alignment map
 *
 * The rules live in `lib/alignment.mjs` and are unit-tested in `alignment.test.mjs`.
 */
import process from "node:process";
import { audit, leadVerb, MASTERY, MASTERY_FLOOR, RANK, sieve } from "./lib/alignment.mjs";
import { loadCourseData } from "./lib/load-data.mjs";

/**
 * Content debt that predates the gate. Every entry names the plan task that
 * closes it. If a listed gap is fixed, the entry goes stale and the build fails
 * until it is deleted — so this cannot become a permanent excuse file.
 *
 * Empty as of Wave 2: every phase ends in a workshop and every objective is both
 * taught and tested. Keep it that way — an entry added here is a promise, and the
 * staleness check is what collects on it.
 */
const KNOWN_GAPS = [];

const { phases } = await loadCourseData();
const { errors, counts } = audit({ phases });
const { live, stale } = sieve(errors, KNOWN_GAPS);

console.log(
  `Alignment scan · ${counts.phases} phases · ${counts.objectives} objectives · ` +
    `${counts.concepts} cards · ${counts.exercises} exercises · ${counts.workshops} workshops`,
);
console.log(
  `Pedagogy    · ${counts.blanks} blank-editor tasks · ${counts.recall} recall checks · ` +
    `${counts.predicts} predict-first prompts`,
);
console.log(
  `Mastery     · ${counts.operates} task(s) reach "operate" — the only rung that ` +
    "produces evidence somebody else would accept",
);

if (process.argv.includes("--report")) {
  for (const phase of phases) {
    console.log(`\n  Phase ${phase.num} · ${phase.title}`);
    for (const o of phase.objectives) {
      const cards = phase.concepts.filter((c) => c.teaches?.includes(o.id)).map((c) => c.id);
      const tasks = [...phase.exercises, ...(phase.workshop ? [phase.workshop] : [])]
        .filter((e) => e.assesses?.includes(o.id))
        .map((e) => e.id);
      const verb = leadVerb(o.text) ?? "?";
      const floor = MASTERY_FLOOR[verb] ?? "?";
      const reached =
        tasks
          .map((id) =>
            [...phase.exercises, ...(phase.workshop ? [phase.workshop] : [])].find(
              (t) => t.id === id,
            ),
          )
          .reduce((best, t) => Math.max(best, RANK.get(t?.proves) ?? -1), -1) ?? -1;
      console.log(
        `    ${o.id.padEnd(13)} ${verb.padEnd(13)} needs ${floor.padEnd(10)} ` +
          `reaches ${(MASTERY[reached] ?? "—").padEnd(10)} ` +
          `taught by ${cards.join(", ") || "—"} · tested by ${tasks.join(", ") || "—"}`,
      );
    }
  }
  console.log("");
}

for (const gap of KNOWN_GAPS) {
  if (!stale.includes(gap))
    console.log(`  known gap · ${gap.subject}: ${gap.why} (${gap.closedBy})`);
}

if (stale.length) {
  console.error(
    `\n${stale.length} stale known-gap entr${stale.length === 1 ? "y" : "ies"} — the gap is fixed, delete the entry:`,
  );
  for (const gap of stale) console.error(`  - ${gap.rule} / ${gap.subject} (${gap.closedBy})`);
}

if (live.length) {
  console.error(`\n${live.length} alignment problem(s):`);
  for (const e of live) console.error(`  - [${e.rule}] ${e.subject}: ${e.message}`);
}

if (live.length || stale.length) process.exit(1);
console.log("\nAlignment OK — every objective is taught before it is tested.");
