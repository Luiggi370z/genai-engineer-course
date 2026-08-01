#!/usr/bin/env node
/**
 * One-shot recovery tool: lifts the course content out of the shipped single-file
 * bundle (`src/course.html`) and writes it back as readable TypeScript modules,
 * one per phase.
 *
 * The bundle's minified JS keeps the course data as plain object literals, so it
 * can be evaluated in a sandbox and re-serialised. Kept in the repo as the audit
 * trail for how `app/src/data/` was produced; it is not part of the build.
 *
 *   node scripts/extract-data.mjs [--bundle ../src/course.html] [--out src/data]
 */
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { readBundleData } from "./lib/bundle-data.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const appRoot = path.resolve(here, "..");

const args = process.argv.slice(2);
const argOf = (flag, fallback) => {
  const i = args.indexOf(flag);
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback;
};

const bundlePath = path.resolve(appRoot, argOf("--bundle", "../src/course.html"));
const outDir = path.resolve(appRoot, argOf("--out", "src/data"));

/** Phase id in the bundle -> slug used for the generated file name. */
const PHASE_SLUGS = {
  p1: "foundations",
  p2: "retrieval",
  p3: "agents",
  p4: "design-defend",
  p5: "mcp",
  p6: "deploy",
  p7: "mindset",
};

/* ---------------------------------------------------------------- serialising */

const INDENT = "  ";

function isPlainObject(v) {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function serialiseString(value) {
  if (!value.includes("\n")) return JSON.stringify(value);
  // Multi-line content (code samples) reads far better as a template literal.
  const body = value.replace(/\\/g, "\\\\").replace(/`/g, "\\`").replace(/\$\{/g, "\\${");
  return `\`${body}\``;
}

function serialise(value, depth) {
  const pad = INDENT.repeat(depth);
  const padInner = INDENT.repeat(depth + 1);

  if (typeof value === "string") return serialiseString(value);
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (value === null) return "null";

  if (Array.isArray(value)) {
    if (value.length === 0) return "[]";
    const allShortStrings =
      value.every((v) => typeof v === "string" && !v.includes("\n")) &&
      value.reduce((n, v) => n + v.length, 0) < 60;
    if (allShortStrings) return `[${value.map((v) => serialiseString(v)).join(", ")}]`;
    const items = value.map((v) => `${padInner}${serialise(v, depth + 1)}`);
    return `[\n${items.join(",\n")},\n${pad}]`;
  }

  if (isPlainObject(value)) {
    const entries = Object.entries(value);
    if (entries.length === 0) return "{}";
    const oneLine = entries.every(([, v]) => typeof v === "string" && !v.includes("\n"));
    const rendered = entries.map(([k, v]) => `${quoteKey(k)}: ${serialise(v, depth + 1)}`);
    if (oneLine && rendered.reduce((n, s) => n + s.length, 0) < 80) {
      return `{ ${rendered.join(", ")} }`;
    }
    return `{\n${rendered.map((r) => padInner + r).join(",\n")},\n${pad}}`;
  }

  throw new Error(`cannot serialise value of type ${typeof value}`);
}

const IDENTIFIER = /^[A-Za-z_$][A-Za-z0-9_$]*$/;
const quoteKey = (k) => (IDENTIFIER.test(k) ? k : JSON.stringify(k));

const HEADER = `// Generated from the shipped course bundle by scripts/extract-data.mjs.
// Edit freely from here on — this file is the source of truth for the content.
`;

function writeFile(relPath, contents) {
  const full = path.join(outDir, relPath);
  fs.mkdirSync(path.dirname(full), { recursive: true });
  fs.writeFileSync(full, contents, "utf8");
  return full;
}

/* --------------------------------------------------------------------- checks */

function countContent(phase) {
  const blocks = [
    ...(phase.concepts ?? []).flatMap((c) => c.blocks ?? []),
    ...(phase.workshop?.blocks ?? []),
  ];
  return {
    objectives: (phase.objectives ?? []).length,
    concepts: (phase.concepts ?? []).length,
    blocks: blocks.length,
    exercises: (phase.exercises ?? []).length,
    deliverables: (phase.workshop?.deliverables ?? []).length,
    checkpoint: (phase.checkpoint ?? []).length,
    qbank: (phase.qbank ?? []).reduce((n, g) => n + g.items.length, 0),
    resources: (phase.resources ?? []).length,
  };
}

/* ----------------------------------------------------------------------- main */

const data = readBundleData(bundlePath);

if (data.phases.length !== 7) {
  throw new Error(`expected 7 phases in the bundle, found ${data.phases.length}`);
}
for (const phase of data.phases) {
  if (!PHASE_SLUGS[phase.id]) throw new Error(`no slug mapped for phase ${phase.id}`);
}

const written = [];

written.push(
  writeFile(
    "intro.ts",
    `${HEADER}
import type { Milestone, Myth, Prerequisite } from "./types";

export const prerequisites: Prerequisite[] = ${serialise(data.prereqs, 0)};

export const myths: Myth[] = ${serialise(data.myths, 0)};

export const milestones: Milestone[] = ${serialise(data.milestones, 0)};
`,
  ),
);

for (const phase of data.phases) {
  const slug = PHASE_SLUGS[phase.id];
  const varName = slug.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
  // `num` is derived from position in phases/index.ts, so it is not persisted.
  const { num: _num, ...rest } = phase;
  written.push(
    writeFile(
      `phases/${slug}.ts`,
      `${HEADER}
import type { PhaseContent } from "../types";

export const ${varName}: PhaseContent = ${serialise(rest, 0)};
`,
    ),
  );
}

const indexBody = data.phases
  .map((p) => {
    const slug = PHASE_SLUGS[p.id];
    const varName = slug.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
    return { slug, varName };
  })
  .map(({ varName }) => `${INDENT}${varName},`)
  .join("\n");

const imports = data.phases
  .map((p) => {
    const slug = PHASE_SLUGS[p.id];
    const varName = slug.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
    return `import { ${varName} } from "./${slug}";`;
  })
  .join("\n");

written.push(
  writeFile(
    "phases/index.ts",
    `${HEADER}
import type { Phase, PhaseContent } from "../types";
${imports}

/** Course order. Phase numbers are derived from this list, never hard-coded. */
const ordered: PhaseContent[] = [
${indexBody}
];

export const phases: Phase[] = ordered.map((phase, i) => ({ ...phase, num: i + 1 }));
`,
  ),
);

console.log(`Extracted from ${path.relative(process.cwd(), bundlePath)}`);
for (const f of written) console.log(`  wrote ${path.relative(appRoot, f)}`);

console.log("\nContent counts (assert these survive any refactor):");
const table = data.phases.map((p) => ({ id: p.id, slug: PHASE_SLUGS[p.id], ...countContent(p) }));
console.table(table);
console.log(
  `prerequisites ${data.prereqs.length} · myths ${data.myths.length} · milestones ${data.milestones.length}`,
);
