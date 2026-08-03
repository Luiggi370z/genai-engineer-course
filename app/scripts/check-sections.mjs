#!/usr/bin/env node
/**
 * Navigation gate: the table of contents has to agree with the page.
 *
 *   pnpm build && node scripts/check-sections.mjs
 *   node scripts/check-sections.mjs --phase 9          # one phase, for a fix loop
 *   node scripts/check-sections.mjs --viewport phone   # one lane
 *
 * Two rules. Click an entry, and that entry is the one that highlights. And arrive
 * at a phase on a phone, and its long sections are folded.
 *
 * The first sounds too obvious to test, and it has now been wrong twice.
 *
 * The first time, the thumb was positioned from scroll metrics on a rail whose
 * rows are evenly spaced, so it drifted rows away from the highlight on phases
 * with one enormous section (`7bf0e2f`). The second time, folding the long
 * sections on a phone brought the headings 84-133px apart against a 159px reading
 * band, so two or three qualified at once and the last one won — tapping
 * "Exercises" highlighted "Workshop".
 *
 * The second rule is here because the bug it catches needs a *sequence* of phases
 * to show up at all, which is what this gate's loop already walks.
 *
 * All three were invisible to every other gate. `check-a11y.mjs` checks that each entry
 * points at an element that exists, which both bugs satisfied: the links were
 * fine, the answer to "where am I" was wrong. That question needs a real browser,
 * because it is entirely about geometry — scroll positions, element heights, and a
 * viewport. jsdom has none of those and reports every element at 0x0.
 *
 * Cost: a browser launch and about a minute for the full matrix. It runs in
 * `verify-full` and in CI, next to the browser accessibility sweep.
 */
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";
import { loadCourseData } from "./lib/load-data.mjs";

const { isLongSection } = await import("../src/lib/section-size.ts");

/** The sections the phone folds, per `PhaseView`. */
const FOLDABLE = ["concepts", "exercises", "workshop", "qbank"];

const here = dirname(fileURLToPath(import.meta.url));
const app = resolve(here, "..");
const argv = process.argv.slice(2);
const onlyPhase = value(argv, "--phase");
const onlyViewport = value(argv, "--viewport");

/**
 * The two lanes, and they are not the same page.
 *
 * Above `xl` the rail is on screen and every section is expanded. Below it the
 * rail is replaced by a chip bar and the long sections are folded, which is the
 * configuration that produced the second bug — so the phone lane is the one that
 * matters most here, and it exists nowhere else in the gates.
 */
const LANES = [
  { name: "desktop", width: 1440, height: 900, nav: "On this page" },
  { name: "phone", width: 390, height: 844, nav: "Sections in this phase" },
];

const htmlPath = resolve(app, "dist/course.html");
try {
  readFileSync(htmlPath);
} catch {
  console.error(`No ${htmlPath} — run \`pnpm build\` first. This gate checks the artifact.`);
  process.exit(1);
}

const { phases: course } = await loadCourseData();
const numbers = onlyPhase ? [Number(onlyPhase)] : range(1, course.length);
const lanes = onlyViewport ? LANES.filter((lane) => lane.name === onlyViewport) : LANES;

const findings = [];
let checked = 0;

const browser = await chromium.launch();
try {
  for (const lane of lanes) {
    const context = await browser.newContext({
      viewport: { width: lane.width, height: lane.height },
      reducedMotion: "reduce",
    });
    const page = await context.newPage();
    await page.goto(`file://${htmlPath}`);
    await page.waitForSelector("#root > *");

    for (const number of numbers) {
      await openPhase(page, number);
      if (lane.name === "phone") await checkFolds(page, number, lane.name);
      const nav = page.getByRole("navigation", { name: lane.nav });
      const labels = (await nav.getByRole("link").allInnerTexts()).map((text) => text.trim());
      if (labels.length === 0) {
        findings.push({
          view: `${lane.name}/phase-${pad(number)}`,
          subject: lane.nav,
          message: "no section entries at all — the navigator is empty or misnamed",
        });
        continue;
      }
      for (const label of labels) {
        await nav.getByRole("link", { name: label, exact: true }).click();
        // The scroll is instant under `reducedMotion: reduce`, but the spy runs
        // off a rAF-throttled scroll handler, so the answer lands a frame later.
        await page.waitForTimeout(250);
        checked++;
        const current = (await nav.locator("[aria-current='location']").allInnerTexts())
          .map((text) => text.trim())
          .join(", ");
        if (current === label) continue;
        findings.push({
          view: `${lane.name}/phase-${pad(number)}`,
          subject: label,
          message: current
            ? `highlights "${current}" instead`
            : "nothing is marked as current afterwards",
        });
      }
      // Leave this phase the way a reader would: unfolded. The arrival check on
      // the *next* phase is only meaningful if something was opened in this one —
      // a gate that never opens a fold cannot see state outliving a phase, which
      // is how a run of this file passed with that bug deliberately reinstated.
      if (lane.name === "phone") await expandFolds(page);
    }
    await context.close();
  }
} finally {
  await browser.close();
}

console.log(
  `Section navigation · ${checked} entries clicked · ${lanes.length} lane(s) × ` +
    `${numbers.length} phase(s) · every click must highlight what it points at` +
    (lanes.some((lane) => lane.name === "phone")
      ? ` · ${numbers.length} phase arrivals checked for folded sections`
      : ""),
);

if (findings.length) {
  console.error(`\n${findings.length} navigation problem(s):\n`);
  for (const f of findings) console.error(`  ${f.view} · "${f.subject}" ${f.message}`);
  console.error(
    "\nA highlight problem is the reading-position rule in `useActiveSection.ts`. Both\n" +
      "past failures came from the band: it has to shrink to fit the shortest section\n" +
      "on the page, and the end of the page has to be answered separately because no\n" +
      "heading can reach the band once scrolling has stopped.\n" +
      "\nA folding problem is per-phase view state outliving the phase. `App.tsx` keys\n" +
      "`PhaseView` by phase id for exactly this reason.\n",
  );
  process.exit(1);
}
console.log("\nSection navigation OK — the table of contents agrees with the page.");

// --- helpers ----------------------------------------------------------------

/**
 * A phase arrives folded, however the reader got there.
 *
 * Checked in this gate rather than a new one because the leak needs a *sequence*
 * to appear, and walking phase to phase in one page is what this loop already
 * does. React keeps the state of a component at the same position in the tree
 * across a route change, and the folds are that state — so before `App.tsx` keyed
 * `PhaseView` by phase, opening the three long sections of phase 1 and walking on
 * delivered every later phase pre-unfolded. Twenty screens of it, on a phone, with
 * the feature silently off. A per-phase check on a fresh page load passes happily.
 */
async function checkFolds(page, number, lane) {
  const phase = course[number - 1];
  const expected = FOLDABLE.filter((id) => isLongSection(phase, id)).length;
  const found = await page.getByRole("button", { name: /^Show / }).count();
  if (found === expected) return;
  findings.push({
    view: `${lane}/phase-${pad(number)}`,
    subject: "folded sections on arrival",
    message:
      `${found} collapsed, expected ${expected} — ` +
      (found < expected
        ? "the phase arrived already open, so per-phase view state is being reused"
        : "more sections fold than `isLongSection` says are long"),
  });
}

/** Opens every fold, re-querying because opening one renames its own trigger. */
async function expandFolds(page) {
  const triggers = page.getByRole("button", { name: /^Show / });
  for (let guard = 0; guard < FOLDABLE.length + 1; guard++) {
    if ((await triggers.count()) === 0) return;
    await triggers.first().click();
    await page.waitForTimeout(40);
  }
}

async function openPhase(page, number) {
  const menu = page.getByRole("button", { name: "Open navigation" });
  const mobile = await menu.isVisible();
  const dialog = page.getByRole("dialog", { name: "Course navigation" });
  if (mobile) {
    await menu.click();
    await dialog.waitFor({ state: "visible" });
  }
  // Scoped to the dialog on a phone: both sidebars are in the DOM and match the
  // same accessible name, so an unscoped click lands on the hidden copy.
  const root = mobile ? dialog : page;
  await root
    .getByRole("navigation", { name: "Phases" })
    .getByRole("button", { name: new RegExp(`Phase ${pad(number)}\\b`) })
    .first()
    .click();
  if (mobile) await dialog.waitFor({ state: "hidden" }).catch(() => {});
  await page.waitForTimeout(200);
}

function pad(number) {
  return String(number).padStart(2, "0");
}

function range(from, to) {
  return Array.from({ length: to - from + 1 }, (_, i) => from + i);
}

function value(args, flag) {
  const index = args.indexOf(flag);
  if (index === -1) return null;
  return args[index + 1] ?? null;
}
