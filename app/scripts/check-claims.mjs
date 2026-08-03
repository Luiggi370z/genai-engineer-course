#!/usr/bin/env node
/**
 * Claims gate: the perishable numbers agree with each other, and none of them
 * ships undated.
 *
 *   node scripts/check-claims.mjs            # gate: exits 1 on drift
 *   node scripts/check-claims.mjs --report   # also list every claim and its age
 *
 * `src/data/reference.ts` is the canonical copy of the hardware tiers, the token
 * prices and the one tag per model role. This walks everything that restates
 * them — the root and release READMEs, the `PRICE` dicts in the Python lessons —
 * and fails when a copy has drifted.
 *
 * Staleness is reported, never failed. See `STALE_DAYS` in `lib/claims.mjs` for
 * why a build that goes red on a date nobody chose makes the numbers *less*
 * trustworthy rather than more.
 */
import { readFileSync } from "node:fs";
import { glob } from "node:fs/promises";
import { dirname, relative, resolve } from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import {
  datasetFindings,
  modelFindings,
  pinFindings,
  priceFindings,
  readDataset,
  STALE_DAYS,
  sourceFindings,
  tableFindings,
} from "./lib/claims.mjs";
import { loadReference } from "./lib/load-data.mjs";

const repo = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const report = process.argv.includes("--report");
const reference = await loadReference();
const {
  HARDWARE,
  hardwareSummaryMarkdown,
  MODELS,
  TOKEN_PRICES,
  VENDORS,
  HARDWARE_VERIFIED,
  VOLATILE,
} = reference;

/**
 * Tags that answer the same question as a canonical model and would quietly
 * become a second one. Authored, not inferred — see `modelFindings`.
 */
const RIVALS = {
  judge: ["qwen3.6:27b"],
  // The cheap Llama Guard everyone reaches for when the 8B feels heavy. It is a
  // different detector with a different false-negative profile, so a lesson
  // quietly screening with it produces containment numbers nobody can compare.
  guard: ["llama-guard3:1b"],
  // The tag the capstone shipped until a release run tried to load it: fastembed
  // has no `bge-reranker-v2-m3`, so naming it took the assistant down at
  // construction while every lesson used `bge-reranker-base` and passed. Two
  // reranker names in one repo is the drift; one of them not existing is what it
  // cost.
  rerank: ["BAAI/bge-reranker-v2-m3"],
};

// Every registered CI-tier tag is a rival of its role's course tag, allowed only
// in the files the registry names. A lane that cannot run the course model is a
// legitimate exception; the same tag leaking into a lesson is not.
//
// Appended rather than spread over the object above: spreading meant registering
// a CI-tier guard would silently delete the authored guard rival, and the gate
// would go quiet about the exact substitution it exists to catch.
for (const model of MODELS.filter((model) => model.tier === "ci")) {
  RIVALS[model.role] = [
    ...(RIVALS[model.role] ?? []),
    { tag: model.tag, exempt: model.onlyIn ?? [] },
  ];
}

/**
 * Libraries more than one lesson teaches, and the import paths their pinned
 * range replaced. Authored for the same reason as `RIVALS`: only a human knows
 * that `ragas.metrics.Faithfulness` and `ragas.metrics.collections.Faithfulness`
 * are two names for one job, and that the first still imports.
 */
const WATCHED_PACKAGES = [
  {
    name: "ragas",
    pin: ">=0.4,<0.5",
    replacement: "ragas.metrics.collections",
    retired: ["from ragas import EvaluationDataset", "from ragas.dataset_schema import"],
  },
];

const findings = [];
const push = (rows) => findings.push(...rows);

// --- 1. every registered claim is sourced and dated -------------------------
const sourced = [...VENDORS, HARDWARE_VERIFIED, ...VOLATILE];
const { errors, stale } = sourceFindings({ claims: sourced });
push(errors);

// --- 2. the README tables still match the canonical rows --------------------
const summary = hardwareSummaryMarkdown();
for (const file of ["README.md", "release/README.md"]) {
  push(
    tableFindings({ file, markdown: readFileSync(resolve(repo, file), "utf8"), expected: summary }),
  );
}

// --- 3. the lesson code prices tokens at the canonical rate -----------------
const pythonFiles = [];
for await (const path of glob("src/**/*.py", { cwd: repo })) {
  pythonFiles.push({ file: path, source: readFileSync(resolve(repo, path), "utf8") });
}
for (const { file, source } of pythonFiles) {
  push(priceFindings({ file, source, prices: TOKEN_PRICES }));
}

// --- 4. one model per role, course-wide -------------------------------------
const roles = MODELS.filter(
  (model) => (model.tier ?? "course") === "course" && RIVALS[model.role],
).map((model) => ({ ...model, rivals: RIVALS[model.role] }));
push(modelFindings({ files: pythonFiles, roles }));

// Markdown and course data restate the tags too, and a README telling you to pull
// the wrong judge is the same defect as code loading it.
const REGISTRY = "app/src/data/reference.ts";
// Compose files and workflows are scanned for the same reason: the tag that got
// a lane running a different model was never going to appear in a .py file.
const proseFiles = [];
for await (const path of glob(
  "{README.md,release/**/*.md,src/**/*.md,app/src/data/**/*.ts,src/**/*.yml,.github/workflows/*.yml,src/verify-*.sh}",
  { cwd: repo },
)) {
  // The registry names every rival tag by definition — that is what makes it the
  // registry. Scanning it would report the list against itself.
  if (path === REGISTRY) continue;
  proseFiles.push({ file: path, source: readFileSync(resolve(repo, path), "utf8") });
}
push(modelFindings({ files: proseFiles, roles }));

// --- 5. every count of the red-team dataset is the dataset's own count ------
const REDTEAM = "src/phase6-design-defend/01-red-team/after/evals/redteam.jsonl";
const dataset = readDataset(readFileSync(resolve(repo, REDTEAM), "utf8"));
push(datasetFindings({ files: [...proseFiles, ...pythonFiles], dataset }));

// --- 6. one pin per library the course teaches twice ------------------------
const manifests = [];
for await (const path of glob("src/**/pyproject.toml", { cwd: repo })) {
  manifests.push({ file: path, source: readFileSync(resolve(repo, path), "utf8") });
}
push(pinFindings({ manifests, sources: pythonFiles, packages: WATCHED_PACKAGES }));

// --- report -----------------------------------------------------------------
console.log(
  `Claims scan · ${sourced.length} sourced claim(s) · ${HARDWARE.length} hardware tiers · ` +
    `${Object.keys(TOKEN_PRICES).length} priced models · ${pythonFiles.length} python files · ` +
    `${manifests.length} manifests`,
);
if (stale.length) {
  console.log(
    `\n  ${stale.length} claim(s) past ${STALE_DAYS} days — re-check, do not just re-date:`,
  );
  for (const row of stale)
    console.log(`    ${String(row.age).padStart(4)}d  ${row.label} · ${row.claim}`);
}
if (report) {
  console.log("\n  Registry:");
  for (const claim of sourced) {
    const label = claim.id ?? claim.vendor ?? "hardware";
    console.log(`    ${claim.verifiedOn}  ${label.padEnd(16)} ${claim.source.url}`);
  }
  console.log("");
}

if (findings.length) {
  console.error(`\n${findings.length} claim problem(s):`);
  for (const f of findings)
    console.error(`  - [${f.rule}] ${relative(".", f.subject)}: ${f.message}`);
  process.exit(1);
}
console.log(
  "\nClaims OK — one hardware table, one price list, one model per role, one pin per library.",
);
