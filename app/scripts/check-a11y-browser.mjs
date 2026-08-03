#!/usr/bin/env node
/**
 * Accessibility gate, tier 2: axe in a real browser, where layout exists.
 *
 *   pnpm build && node scripts/check-a11y-browser.mjs
 *   node scripts/check-a11y-browser.mjs --report        # list every view scanned
 *   node scripts/check-a11y-browser.mjs --phase 3       # one phase, for a fix loop
 *
 * `check-a11y.mjs` runs axe under jsdom and documents its own blind spot in its
 * header: no layout engine, so `color-contrast` and `scrollable-region-focusable`
 * come back **incomplete** rather than pass or fail. Incomplete results are not
 * reported by that gate, which means the two rules most likely to be broken by an
 * ordinary CSS edit were the two nothing checked. The round-3 audit found four
 * phase accents under 4.5:1 and three unreachable scroll containers — every one
 * of them in code the jsdom gate had already passed.
 *
 * So this one loads `dist/course.html` in Chromium and scans a matrix:
 *
 *   2 viewports  × 2 themes × (dashboard + every phase)
 *   1280×800 desktop, 390×844 phone — the phone matters on its own terms,
 *   because the sidebar becomes a dialog and the section rail becomes a
 *   horizontally scrolling chip bar, and that chip bar is a scroll container
 *   that only exists at that width.
 *
 * Both tiers stay. This one needs a browser download and takes about a minute;
 * the jsdom tier runs in two seconds and is what a pre-commit hook can afford.
 * A gate nobody can run locally becomes a gate everybody skips.
 *
 * Reading a failure: axe names the rule, the element and the measured values —
 * for contrast, the actual ratio and the required one. Fix the token, not the
 * instance; every accent in this workbook comes from `src/data/phases/*.ts` and
 * `check-a11y.mjs` computes them against both card backgrounds, so a contrast
 * failure here usually means that rule needs to know about a colour it has not
 * been told about.
 */
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import AxeBuilder from "@axe-core/playwright";
import { chromium } from "playwright";
import { loadCourseData } from "./lib/load-data.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const app = resolve(here, "..");
const argv = process.argv.slice(2);
const report = argv.includes("--report");
const onlyPhase = value(argv, "--phase");

/** The rule sets, plus the two this tier exists for. */
const AXE_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "best-practice"];

const VIEWPORTS = [
  { name: "desktop", width: 1280, height: 800 },
  // The phone is not "the desktop, narrower". The sidebar becomes a modal
  // dialog and the section rail becomes a horizontal chip bar — different
  // markup, different focus order, and a scroll container that exists nowhere
  // else.
  { name: "phone", width: 390, height: 844 },
];

const THEMES = ["light", "dark"];

const htmlPath = resolve(app, "dist/course.html");
try {
  readFileSync(htmlPath);
} catch {
  console.error(`No ${htmlPath} — run \`pnpm build\` first. This gate checks the artifact.`);
  process.exit(1);
}

// From the content modules, not a constant: adding a tenth phase must widen the
// scan without anybody remembering to edit this file.
const { phases: course } = await loadCourseData();
const phases = onlyPhase ? [Number(onlyPhase)] : range(1, course.length);

const findings = [];
const scanned = [];

const browser = await chromium.launch();
try {
  for (const viewport of VIEWPORTS) {
    for (const theme of THEMES) {
      const context = await browser.newContext({
        viewport: { width: viewport.width, height: viewport.height },
        colorScheme: theme,
        // Reduced motion off the animation path: a transition mid-scan makes
        // axe measure a colour that exists for 200ms and belongs to nobody.
        reducedMotion: "reduce",
      });
      const page = await context.newPage();
      // The theme is persisted, and the app reads it on mount — so it has to be
      // in place before the first paint, not toggled afterwards. Toggling would
      // also work and would scan a page mid-transition.
      await page.addInitScript(
        (value) => window.localStorage.setItem("genai_workbook_theme", value),
        theme,
      );
      await page.goto(`file://${htmlPath}`);
      await page.waitForSelector("#root > *");

      await scan(page, `${viewport.name}/${theme}/dashboard`);
      if (viewport.name === "phone") {
        // The open nav is a view of its own — a modal dialog with its own
        // roles and its own scrolling rail, on screen only at this width.
        await page.getByRole("button", { name: "Open navigation" }).click();
        await page.getByRole("dialog", { name: "Course navigation" }).waitFor();
        await scan(page, `${viewport.name}/${theme}/nav-open`);
        await page.keyboard.press("Escape");
        await page.getByRole("dialog").waitFor({ state: "hidden" });
      }
      for (const phase of phases) {
        await openPhase(page, phase, `${viewport.name}/${theme}`);
        // A phone folds the long sections away by default, so scanning as-loaded
        // would quietly stop checking the contrast of most of the course at the
        // width where it is hardest to read. Opening them first keeps the scan
        // over the same content it covered before the fold existed — and the
        // trigger is on screen either way, so nothing is lost by not scanning the
        // closed state.
        await expandSections(page);
        await scan(page, `${viewport.name}/${theme}/phase-${String(phase).padStart(2, "0")}`);
      }
      await context.close();
    }
  }
} finally {
  await browser.close();
}

console.log(
  `Browser a11y · ${scanned.length} views · ${VIEWPORTS.length} viewports × ` +
    `${THEMES.length} themes × ${phases.length + 1} routes (+ the phone nav dialog) · ` +
    `${AXE_TAGS.length} rule sets · contrast and scrollable-region-focusable INCLUDED`,
);
if (report) {
  console.log("");
  for (const view of scanned) console.log(`    ${view}`);
  console.log("");
}

if (findings.length) {
  // Grouped by rule, because one bad token produces forty findings and a flat
  // list makes that look like forty problems.
  const byRule = new Map();
  for (const f of findings) byRule.set(f.rule, [...(byRule.get(f.rule) ?? []), f]);
  console.error(`\n${findings.length} accessibility problem(s) in a real browser:\n`);
  for (const [rule, rows] of [...byRule].sort((a, b) => b[1].length - a[1].length)) {
    console.error(`  [${rule}] ${rows.length} — ${rows[0].help}`);
    for (const row of rows.slice(0, 6)) console.error(`      ${row.view} · ${row.target}`);
    if (rows.length > 6) console.error(`      … and ${rows.length - 6} more`);
  }
  process.exit(1);
}
console.log("\nBrowser a11y OK — contrast and scroll reachability hold in both themes.");

// --- helpers ----------------------------------------------------------------

async function scan(page, view) {
  scanned.push(view);
  const results = await new AxeBuilder({ page }).withTags(AXE_TAGS).analyze();
  for (const violation of results.violations) {
    for (const node of violation.nodes) {
      findings.push({
        rule: `axe/${violation.id}`,
        view,
        target: node.target.join(" "),
        help: violation.help,
        // The measured values, which is the difference between "fix the
        // contrast" and "3.9:1 against #1c211f, needs 4.5:1".
        detail: (node.any ?? []).map((c) => c.message).join("; "),
      });
    }
  }
}

/**
 * Open every folded phase section, so the scan sees the whole page.
 *
 * A no-op above the `xl` breakpoint, where nothing folds and no trigger exists.
 * Matched on the accessible name rather than a test id, which means a rename that
 * makes the control unreadable also makes this stop finding it.
 */
async function expandSections(page) {
  const triggers = page.getByRole("button", { name: /^Show / });
  // Re-queried each time: opening a section changes its own label to "Hide", so
  // the collection shrinks as it is worked through.
  for (let guard = 0; guard < 12; guard++) {
    const next = triggers.first();
    if ((await triggers.count()) === 0) return;
    await next.click();
    await page.waitForTimeout(30);
  }
}

async function openPhase(page, number, view) {
  const label = `Phase ${String(number).padStart(2, "0")}`;
  const menu = page.getByRole("button", { name: "Open navigation" });
  // On the phone the sidebar lives behind the menu button; on the desktop it is
  // always on screen. Asking the page rather than branching on the width keeps
  // this honest if the breakpoint moves.
  const mobile = await menu.isVisible();
  const dialog = page.getByRole("dialog", { name: "Course navigation" });
  if (mobile) {
    await menu.click();
    // React renders the dialog a tick after the click, and `count()` below does
    // not auto-wait — without this the phone lane reports a missing phase link.
    await dialog.waitFor({ state: "visible" });
  }
  // Both sidebars are in the DOM on a phone — the desktop one is display:none
  // behind the dialog, and it matches the same accessible name. Scoping to the
  // dialog is what stops the click landing on the hidden copy.
  const root = mobile ? dialog : page;
  // Not anchored at the start: the progress ring contributes "0% complete" to
  // the button's accessible name before the phase label. Scoped to the Phases
  // landmark so the dashboard's phase cards cannot answer for the sidebar.
  const link = root
    .getByRole("navigation", { name: "Phases" })
    .getByRole("button", { name: new RegExp(`${label}\\b`) })
    .first();
  if ((await link.count()) === 0) {
    findings.push({
      rule: "navigation",
      view,
      target: label,
      help: `no ${label} control in the navigation`,
      detail: "",
    });
    return;
  }
  await link.click();
  // The dialog closes itself on navigate; wait for that rather than for a
  // heading, so a content rename never turns into a flaky a11y gate.
  if (mobile)
    await page
      .getByRole("dialog")
      .waitFor({ state: "hidden" })
      .catch(() => {});
  await page.waitForTimeout(150);
}

function range(from, to) {
  return Array.from({ length: to - from + 1 }, (_, i) => from + i);
}

function value(args, flag) {
  const index = args.indexOf(flag);
  if (index === -1) return null;
  return args[index + 1] ?? null;
}
