/**
 * Reads the course data out of a shipped single-file bundle.
 *
 * The bundle's minified JS keeps the content as plain object literals, so the
 * declaration region can be sliced out and evaluated in a sandbox.
 */
import fs from "node:fs";
import vm from "node:vm";

const REGION_START = 'let c=[{id:"pre-1"';
const REGION_END_ANCHOR = "p=[{stage:";

export function findMatchingClose(source, openIndex) {
  let depth = 0;
  let inString = null;
  let escaped = false;
  for (let i = openIndex; i < source.length; i++) {
    const ch = source[i];
    if (inString) {
      if (escaped) escaped = false;
      else if (ch === "\\") escaped = true;
      else if (ch === inString) inString = null;
      continue;
    }
    if (ch === '"' || ch === "'" || ch === "`") inString = ch;
    else if (ch === "[" || ch === "{" || ch === "(") depth++;
    else if (ch === "]" || ch === "}" || ch === ")") {
      depth--;
      if (depth === 0) return i;
    }
  }
  throw new Error(`unbalanced brackets from index ${openIndex}`);
}

export function readBundleData(bundlePath) {
  const html = fs.readFileSync(bundlePath, "utf8");
  const script = html.match(/<script[^>]*>([\s\S]*?)<\/script>/);
  if (!script) throw new Error(`no <script> found in ${bundlePath}`);
  const js = script[1];

  const start = js.indexOf(REGION_START);
  if (start < 0) {
    throw new Error(`data region anchor not found in ${bundlePath} — is this the original bundle?`);
  }
  const lastArrayOpen = js.indexOf("[", js.indexOf(REGION_END_ANCHOR, start));
  const region = js.slice(start, findMatchingClose(js, lastArrayOpen) + 1);

  return vm.runInNewContext(
    `(function(){ ${region};
       return { prereqs: c, myths: d, phases: h, milestones: p };
     })()`,
    Object.create(null),
    { timeout: 5000 },
  );
}
