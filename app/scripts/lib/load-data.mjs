/**
 * Compiles the TypeScript content modules to one ESM file and imports the real
 * values, so a script reads exactly what the app renders — no parsing, no drift.
 */
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import * as esbuild from "esbuild";

const appRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");

export async function loadCourseData() {
  return compile(`export { phases } from "./src/data/phases/index";
                  export { prerequisites, myths, milestones } from "./src/data/intro";
                  export { electives } from "./src/data/electives";`);
}

/** The canonical hardware/price/model tables, for the claims gate. */
export async function loadReference() {
  return compile(`export * from "./src/data/reference";`);
}

async function compile(contents) {
  const entry = path.join(os.tmpdir(), `workbook-data-${process.pid}-${Date.now()}.mjs`);
  await esbuild.build({
    stdin: { contents, resolveDir: appRoot, loader: "ts" },
    bundle: true,
    format: "esm",
    platform: "neutral",
    outfile: entry,
  });
  try {
    return await import(`file://${entry}`);
  } finally {
    fs.rmSync(entry, { force: true });
  }
}

export { appRoot };
