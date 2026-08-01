#!/usr/bin/env node
/**
 * Readability gate: paragraph length, per-card budgets, deep-dive limits, TL;DR
 * length and flow shapes.
 *
 * The audit that prompted these rules found the workbook's real risk was not being
 * wrong but being unreadable — long unbroken prose, cards carrying three ideas, and
 * diagrams drawn in a shape that contradicted the text beside them. None of that
 * fails a type-check, so it needs its own gate.
 *
 *   node scripts/check-density.mjs            # gate: exits 1 on any violation
 *   node scripts/check-density.mjs --report   # also print the per-card measurements
 *
 * The rules live in `lib/density.mjs` and are unit-tested in `density.test.mjs`.
 */
import process from "node:process";
import { audit, LIMITS, visibleProse } from "./lib/density.mjs";
import { loadCourseData } from "./lib/load-data.mjs";

const { phases } = await loadCourseData();
const { errors, counts } = audit({ phases });

console.log(
  `Density scan · ${counts.cards} cards · median ${counts.medianProse} chars · ` +
    `longest ${counts.maxProse} · caps ${LIMITS.cardProse} prose / ${LIMITS.cardBlocks} blocks`,
);
console.log(
  `Disclosure  · ${counts.deepDives} deep dive(s) · ${counts.shaped} non-linear diagram(s)`,
);

if (process.argv.includes("--report")) {
  for (const phase of phases) {
    console.log(`\n  Phase ${phase.num} · ${phase.title} · TL;DR ${phase.tldr.length} chars`);
    for (const card of phase.concepts) {
      const prose = visibleProse(card.blocks).join(" ").length;
      const dives = (card.blocks ?? []).filter((b) => b.kind === "deepdive").length;
      console.log(
        `    ${card.id.padEnd(14)} ${String(prose).padStart(5)} chars · ` +
          `${String(card.blocks?.length ?? 0).padStart(2)} blocks${dives ? ` · ${dives} deep dive` : ""}`,
      );
    }
  }
  console.log("");
}

if (errors.length) {
  console.error(`\n${errors.length} density problem(s):`);
  for (const e of errors) console.error(`  - [${e.rule}] ${e.subject}: ${e.message}`);
  process.exit(1);
}
console.log("\nDensity OK — every card is inside the budget.");
