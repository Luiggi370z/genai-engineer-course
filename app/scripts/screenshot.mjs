#!/usr/bin/env node
/**
 * Photographs every block kind, in light and in dark.
 *
 * The workbook ships as one HTML file with two themes, and a block kind can be
 * perfectly valid data, pass all three gates, and still be unreadable in dark mode
 * — a hard-coded colour, a border that vanishes, a diagram whose connectors are
 * drawn in ink on ink. Nothing else in the repo would notice.
 *
 * Coverage is **derived, not listed**: the script reads the same course data the
 * app renders, finds a card for each block kind, and drives the page to it. Add a
 * kind and it is photographed on the next run without editing this file; author a
 * kind that nothing in the course uses and it is reported rather than skipped.
 *
 *   node scripts/screenshot.mjs           # both themes into screenshots/
 *   node scripts/screenshot.mjs --dark    # one theme
 *
 * Playwright is deliberately **not** a dependency: it drags a browser download
 * behind it, and nobody editing course content should pay that on `pnpm install`.
 * The script asks for it only when run.
 */
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { KNOWN_KINDS } from "./lib/density.mjs";
import { appRoot, loadCourseData } from "./lib/load-data.mjs";

const bundle = path.join(appRoot, "dist/course.html");
const outDir = path.join(appRoot, "screenshots");
/** Wide enough for the `xl` breakpoint, so the sticky TOC rail is in shot. */
const VIEWPORT = { width: 1440, height: 1000 };

const chromium = await loadPlaywright();
if (!fs.existsSync(bundle)) {
  console.error(`No bundle at ${bundle} — run \`pnpm build\` first.`);
  process.exit(1);
}

const { phases } = await loadCourseData();
const { targets, missing } = planShots(phases);

const only = ["light", "dark"].find((theme) => process.argv.includes(`--${theme}`));
const themes = only ? [only] : ["light", "dark"];

const browser = await chromium.launch();
let taken = 0;

for (const theme of themes) {
  const context = await browser.newContext({ viewport: VIEWPORT, colorScheme: theme });
  // The app reads its theme from localStorage on mount, so set it before the
  // first paint rather than clicking the toggle and waiting for a transition.
  await context.addInitScript((value) => {
    localStorage.setItem("genai_workbook_theme", value);
  }, theme);

  const page = await context.newPage();
  await page.goto(`file://${bundle}`);
  await page.waitForSelector("aside nav");

  let currentPhase = null;
  for (const shot of targets) {
    if (shot.phase.id !== currentPhase) {
      await page.locator("aside nav button").filter({ hasText: shot.phase.title }).first().click();
      await page.waitForSelector("#concepts");
      currentPhase = shot.phase.id;
    }

    // Attribute form rather than `#id`, so an id is never parsed as a selector.
    const card = page.locator(`[id="${shot.card.id}"]`);
    await card.scrollIntoViewIfNeeded();
    await fit(page, card);
    await shoot(card, theme, `${shot.variant.replace(":", "-")}-${shot.card.id}`);

    // A disclosure photographed shut proves only that its handle renders. Both
    // states matter, and the open one is the only way to see a nested block at all.
    const discloses = shot.kind === "deepdive" || shot.kind === "predict" || shot.nested;
    if (discloses) {
      const trigger = card.locator("button[aria-expanded]").first();
      await trigger.click();
      await page.waitForTimeout(200);
      await fit(page, card);
      await shoot(card, theme, `${shot.variant.replace(":", "-")}-${shot.card.id}-open`);
      await trigger.click();
    }
    await page.setViewportSize(VIEWPORT);
  }

  // The phase header carries the TL;DR, the reading time and the TOC rail — none
  // of which belongs to a card, and all of which is theme-sensitive chrome.
  await page.locator("aside nav button").filter({ hasText: phases[0].title }).first().click();
  await page.waitForSelector("#concepts");
  await shoot(page, theme, "phase-header", { clip: { x: 0, y: 0, ...VIEWPORT } });

  await context.close();
}

await browser.close();

console.log(`\n${taken} screenshot(s) in ${path.relative(process.cwd(), outDir)}/`);
for (const [variant, where] of coverage(targets)) console.log(`  ${variant.padEnd(15)} ${where}`);
if (missing.length) {
  console.error(`\n${missing.length} block kind(s) no card uses: ${missing.join(", ")}`);
  console.error("Either the course lost its last instance, or the kind is dead code.");
  process.exit(1);
}

/**
 * Grows the viewport to the height of the card before photographing it.
 *
 * The app scrolls an inner container rather than the window, and Chromium will not
 * stitch a screenshot across one: anything outside the visible band comes back
 * blank. A card taller than the viewport — which the longer concept cards are —
 * would otherwise be photographed as a strip of correct content above a rectangle
 * of nothing, which looks exactly like a rendering bug and is not one.
 *
 * Resizing also re-runs the flow diagrams' `ResizeObserver`, so their connectors
 * are measured against the size they are actually shot at.
 */
async function fit(page, card) {
  const height = await card.evaluate((el) => Math.ceil(el.getBoundingClientRect().height));
  if (height <= VIEWPORT.height) return;
  await page.setViewportSize({ width: VIEWPORT.width, height: height + 120 });
  await page.waitForTimeout(150);
  await card.scrollIntoViewIfNeeded();
}

async function shoot(target, theme, name, options = {}) {
  const file = path.join(outDir, theme, `${name}.png`);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  await target.screenshot({ path: file, ...options });
  taken += 1;
}

/**
 * What actually renders differently, which is finer-grained than the block kind.
 *
 * A `flow` is three renderers behind one kind — the linear flex path and the two
 * SVG shapes — and photographing whichever happens to come first in the course
 * would have covered `linear` nine times and the cycle never. Callout tones are
 * three different colour treatments, which is precisely the sort of thing that
 * survives light mode and dies in dark.
 */
function variantOf(block) {
  if (block.kind === "flow") return `flow:${block.shape ?? "linear"}`;
  if (block.kind === "callout") return `callout:${block.tone}`;
  return block.kind;
}

/**
 * One card per variant — the first that uses it.
 *
 * A variant whose only appearance is *inside* a deep dive still earns a shot; it
 * just needs the disclosure opened to be visible, which `nested` records. Marking
 * such a variant covered without photographing it is how `callout:warn` first went
 * missing here despite twenty-eight uses in the course.
 */
function planShots(phases) {
  const targets = [];
  const found = new Set();

  const consider = (phase, card, blocks, nested) => {
    for (const block of blocks ?? []) {
      const variant = variantOf(block);
      if (!found.has(variant)) {
        found.add(variant);
        targets.push({ kind: block.kind, variant, phase, card, nested });
      }
      if (block.kind === "deepdive") consider(phase, card, block.blocks, true);
    }
  };

  for (const phase of phases) {
    for (const card of phase.concepts) consider(phase, card, card.blocks, false);
  }

  targets.sort((a, b) => a.phase.num - b.phase.num);
  const kinds = new Set([...found].map((variant) => variant.split(":")[0]));
  const missing = [...KNOWN_KINDS].filter((kind) => !kinds.has(kind));
  return { targets, missing };
}

function coverage(shots) {
  return shots.map((shot) => [shot.variant, `${shot.phase.id} · ${shot.card.id}`]);
}

/**
 * Resolved at run time so the package stays out of `package.json`. If it is not
 * there, say exactly what to type — an error naming a module nobody installed on
 * purpose is a puzzle, not a message.
 */
async function loadPlaywright() {
  try {
    return (await import("playwright")).chromium;
  } catch {
    console.error(
      "This script needs Playwright, which is intentionally not a dependency.\n\n" +
        "  pnpm add -D playwright && pnpm exec playwright install chromium\n\n" +
        "Remove it again afterwards if you would rather not keep the browser around.",
    );
    process.exit(1);
  }
}
