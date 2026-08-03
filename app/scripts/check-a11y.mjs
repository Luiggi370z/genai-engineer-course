#!/usr/bin/env node
/**
 * Accessibility gate: axe on the shipped page, plus a keyboard journey through it.
 *
 *   pnpm build && node scripts/check-a11y.mjs
 *   node scripts/check-a11y.mjs --report   # also list the axe passes and the tab order
 *
 * Runs against `dist/course.html` — the actual artifact, mounted and mounted-once,
 * rather than a component rendered in isolation. Isolated component tests would be
 * faster and would have missed both problems this gate found on its first run: a
 * phase title outside every landmark, and two navs called "navigation".
 *
 * Three things happen here, in order of how much they cost:
 *
 *   1. the keyboard rules in `lib/a11y.mjs`, on the dashboard as it first loads
 *   2. a journey — open the mobile nav, Escape out of it, switch to a phase — with
 *      the rules re-run at each stop, because state is where focus goes to die
 *   3. axe, on the dashboard and on a phase, for everything a machine can decide
 *      from markup
 *
 * Not run inside `pnpm test`: it needs a build, and `node --test` should stay a
 * sub-second loop. It runs in `pnpm verify` and in CI, after the build.
 *
 * A known blind spot, stated rather than hidden: jsdom has no layout engine, so
 * colour contrast, focus-visible and scroll-container reachability cannot be
 * decided here — axe reports them as *incomplete*, and incomplete results are not
 * failures. `check-a11y-browser.mjs` covers exactly those rules in Chromium across
 * both viewports and both themes. This tier stays because it runs in two seconds
 * with no browser download; that one runs in `pnpm verify-full` and in CI.
 */
import { readFileSync } from "node:fs";
import { glob } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { JSDOM, VirtualConsole } from "jsdom";
import {
  accentContrastFindings,
  accentFillFindings,
  keyboardFindings,
  landmarks,
  MAX_LANDMARKS,
  MIN_CONTRAST,
  MIN_NAV_LABEL_PX,
  motionFindings,
  navLabelFindings,
  scrimsFrom,
  scrollRegionFindings,
} from "./lib/a11y.mjs";
import { loadCourseData } from "./lib/load-data.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const app = resolve(here, "..");
const report = process.argv.includes("--report");

/**
 * The surfaces a phase accent is drawn on, per theme, from `src/styles/index.css`.
 * `--color-card` is every card and the sidebar; `--color-paper` is the page
 * behind them.
 */
const SURFACES = {
  light: { card: "#ffffff", paper: "#f6f7f4" },
  dark: { card: "#1c211f", paper: "#111413" },
};
// Both matter: a phase chip on the dashboard sits on a card, and the same chip
// in the sticky section bar sits on paper. Paper is the tighter of the two in
// light mode, which is where the first attempt at this palette came up short.

/**
 * Every rendered component, for the label-size floor.
 *
 * This used to be four hand-listed navigation files, on the theory that nav
 * chrome is the type a reader cannot skip. The round-3 audit then found 9.5px
 * kickers on exercise cards, callouts and the electives shelf — all outside the
 * list. A floor with an allowlist is not a floor.
 */
async function labelSources() {
  // The stylesheet is in here for one control: the skip link is styled in CSS,
  // not by a utility class, so a `.tsx`-only scan called the floor clean while
  // the first tab stop on the page sat below it.
  const files = ["src/App.tsx", "src/styles/index.css"];
  for await (const path of glob("src/components/**/*.tsx", { cwd: app })) files.push(path);
  return files.sort();
}

/**
 * Every source file, for the motion rule.
 *
 * Wider than `labelSources` on purpose, and the difference is the whole point:
 * the scroll that ignored the motion preference lives in
 * `components/phase/useActiveSection.ts`, a `.ts` file the label floor's
 * `.tsx`-only glob never opened.
 */
async function motionSources() {
  const files = [];
  for await (const path of glob("src/**/*.ts", { cwd: app })) files.push(path);
  for await (const path of glob("src/**/*.tsx", { cwd: app })) files.push(path);
  return files.sort();
}

const AXE_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "best-practice"];

const findings = [];
const fail = (rule, subject, message) => findings.push({ rule, subject, message });

// --- mount the shipped page -------------------------------------------------
// The inline bundle is a module script, which jsdom will not execute. Pulling the
// scripts out and evaluating them once the DOM exists is the same thing a browser
// does with `type="module"`: parse first, run after.
const htmlPath = resolve(app, "dist/course.html");
let raw;
try {
  raw = readFileSync(htmlPath, "utf8");
} catch {
  console.error(
    `No ${htmlPath} — run \`pnpm build\` first. This gate checks the artifact, not the source.`,
  );
  process.exit(1);
}
const inlineScripts = [...raw.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
const shell = raw.replace(/<script[^>]*>[\s\S]*?<\/script>/g, "");

const virtualConsole = new VirtualConsole();
const crashes = [];
virtualConsole.on("jsdomError", (error) => crashes.push(error.message));

const dom = new JSDOM(shell, {
  runScripts: "dangerously",
  pretendToBeVisual: true,
  url: "http://localhost/",
  virtualConsole,
});
const { window } = dom;
const doc = window.document;

// jsdom ships no layout engine, so the four browser APIs the workbook uses to
// answer "where am I on the page" simply do not exist. Stubbing them is not
// papering over a bug: without them the tree throws on mount and this gate would
// pass a blank document. What they cannot fake is geometry, which is why the
// section-navigator checks below assert on markup and wiring, never on position.
window.IntersectionObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
};
window.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
};
window.Element.prototype.scrollTo = function scrollTo() {};
window.Element.prototype.scrollIntoView = function scrollIntoView() {};

for (const source of inlineScripts) window.eval(source);
await tick(50);

if (!doc.getElementById("root")?.children.length) {
  console.error("The page did not mount in jsdom:");
  for (const crash of crashes) console.error(`  ${crash.split("\n")[0]}`);
  process.exit(1);
}

// --- 1. the dashboard, as it loads -----------------------------------------
collect("dashboard", keyboardFindings(doc));

// --- 2. the journey ---------------------------------------------------------
// Everything below drives the real handlers. Nothing is stubbed: if `App.tsx`
// stops returning focus to the menu button, this notices.
const menu = byLabel("Open navigation");
if (!menu) {
  fail("journey", "mobile nav", "no 'Open navigation' control — a phone has no other way in");
} else {
  click(menu);
  await tick();

  const dialog = doc.querySelector("[role='dialog']");
  if (!dialog) {
    fail("journey", "mobile nav", "the menu button did not open a dialog");
  } else {
    if (dialog.getAttribute("aria-modal") !== "true") {
      fail(
        "journey",
        "mobile nav",
        "the drawer is a dialog but not aria-modal, so a reader keeps reading the page behind it",
      );
    }
    if (menu.getAttribute("aria-expanded") !== "true") {
      fail(
        "journey",
        "mobile nav",
        "the menu button does not report aria-expanded=true while open",
      );
    }
    if (doc.activeElement !== dialog && !dialog.contains(doc.activeElement)) {
      fail(
        "journey",
        "mobile nav",
        "focus stayed outside the drawer — the next Tab walks the page underneath",
      );
    }
    collect("mobile nav open", keyboardFindings(doc));

    // Escape, the one key every dialog owes you.
    key("Escape");
    await tick();
    if (doc.querySelector("[role='dialog']")) {
      fail("journey", "mobile nav", "Escape did not close the drawer");
    } else if (doc.activeElement !== menu) {
      fail(
        "journey",
        "mobile nav",
        "focus did not come back to the menu button — a keyboard user lands at the top of the document instead",
      );
    }
  }
}

// Into a phase, which is where all the section chrome lives.
const phaseButton = [...doc.querySelectorAll("nav button")].find((el) =>
  /^Phase 01/.test(el.textContent ?? ""),
);
if (!phaseButton) {
  fail("journey", "sidebar", "no Phase 01 button in the nav");
} else {
  click(phaseButton);
  await tick();
  if (phaseButton.getAttribute("aria-current") !== "page") {
    fail("journey", "sidebar", "the active phase does not carry aria-current=page");
  }
  collect("phase view", keyboardFindings(doc));
  // Here rather than at the end: the code blocks and the wide tables only exist
  // inside a phase, and they are the scroll containers this rule is about.
  collect("phase view", scrollRegionFindings(doc));

  // Both section navigators, and every chip in them, must point at a heading that
  // is actually on the page. A dead entry in a table of contents is a keyboard
  // user pressing Enter and going nowhere, silently.
  const sectionNavs = [
    ...doc.querySelectorAll(
      "nav[aria-label='On this page'], nav[aria-label='Sections in this phase']",
    ),
  ];
  if (sectionNavs.length < 2) {
    fail(
      "sections",
      "phase view",
      `${sectionNavs.length} section navigator(s) — the wide rail and the narrow chip bar should both be in the DOM`,
    );
  }
  for (const nav of sectionNavs) {
    for (const link of nav.querySelectorAll("a[href^='#']")) {
      const id = link.getAttribute("href").slice(1);
      if (!doc.getElementById(id)) {
        fail(
          "sections",
          `${nav.getAttribute("aria-label")} → ${id}`,
          "points at a section that is not on the page",
        );
      }
    }
  }
}

// --- 3. axe, on both views --------------------------------------------------
window.eval(readFileSync(resolve(app, "node_modules/axe-core/axe.min.js"), "utf8"));
const axeResults = [];
// The phase view first, because that is where the DOM currently is and it carries
// the most chrome; then back to the dashboard, which owns the manifest panel.
await runAxe("phase view");
const dashButton = [...doc.querySelectorAll("nav button")].find((el) =>
  /^Dashboard/.test((el.textContent ?? "").trim()),
);
if (dashButton) {
  click(dashButton);
  await tick();
  await runAxe("dashboard");
}

// --- the label-size floor ---------------------------------------------------
const sources = Object.fromEntries(
  [...(await labelSources())].map((file) => [file, readFileSync(resolve(app, file), "utf8")]),
);
collect("labels", navLabelFindings(sources, MIN_NAV_LABEL_PX, "label-size"));

// --- motion the preference cannot reach -------------------------------------
const motion = Object.fromEntries(
  [...(await motionSources())].map((file) => [file, readFileSync(resolve(app, file), "utf8")]),
);
collect("motion", motionFindings(motion));

// --- phase accents, against the surfaces they are drawn on ------------------
// Data, not DOM: jsdom resolves every custom property to nothing, so the only
// honest place to check a palette here is the palette. The browser tier measures
// the rendered pixels.
const { phases } = await loadCourseData();
collect("accents", accentContrastFindings(phases, SURFACES));

// The inverse job: the accent as a fill, white on top. Read out of the stylesheet
// so the check tracks the shipped scrim instead of a copy of it.
const scrims = scrimsFrom(readFileSync(resolve(app, "src/styles/index.css"), "utf8"));
for (const theme of Object.keys(SURFACES)) {
  if (theme in scrims) continue;
  collect("accents", [
    {
      rule: "accent-fill",
      subject: theme,
      message: "no --accent-scrim declared for this theme in src/styles/index.css",
    },
  ]);
}
collect("accents", accentFillFindings(phases, scrims));

// --- scroll containers, on the dashboard too --------------------------------
collect("dashboard", scrollRegionFindings(doc));

// --- report -----------------------------------------------------------------
console.log(
  `A11y scan · ${doc.querySelectorAll("button, a[href], input").length} controls · ` +
    `axe ${AXE_TAGS.length} rule sets · ${Object.keys(sources).length} components at the ` +
    `${MIN_NAV_LABEL_PX}px label floor · ${phases.length} accents × ` +
    `${Object.keys(SURFACES).length} themes at ${MIN_CONTRAST}:1 · ` +
    // Printed because the number is the finding: the deploy phase offered 16 of
    // these when every code block was one, and a count nobody prints is a
    // regression nobody notices until it is in an audit.
    `${landmarks(doc).length}/${MAX_LANDMARKS} landmarks`,
);
if (report) {
  const stops = [...doc.querySelectorAll("a[href], button:not([disabled]), input:not([disabled])")];
  console.log(`\n  Tab order (${stops.length} stops), first 20:`);
  for (const el of stops.slice(0, 20)) {
    console.log(
      `    ${el.tagName.toLowerCase().padEnd(7)} ${(el.textContent || el.getAttribute("aria-label") || "").trim().slice(0, 56)}`,
    );
  }
  for (const [view, result] of axeResults) {
    console.log(`\n  axe · ${view} · ${result.violations.length} violation(s)`);
  }
  console.log("");
}

if (findings.length) {
  console.error(`\n${findings.length} accessibility problem(s):`);
  for (const f of findings) console.error(`  - [${f.rule}] ${f.subject}: ${f.message}`);
  process.exit(1);
}
console.log("\nA11y OK — the page is reachable, nameable and driveable from the keyboard.");

// --- helpers ----------------------------------------------------------------
function collect(view, rows) {
  for (const row of rows) fail(row.rule, `${view} · ${row.subject}`, row.message);
}

async function runAxe(view) {
  const result = await window.axe.run(doc, {
    resultTypes: ["violations"],
    runOnly: { type: "tag", values: AXE_TAGS },
  });
  axeResults.push([view, result]);
  for (const violation of result.violations) {
    for (const node of violation.nodes) {
      fail(`axe/${violation.id}`, `${view} · ${node.target.join(" ")}`, violation.help);
    }
  }
}

function byLabel(label) {
  return doc.querySelector(`[aria-label='${label}']`);
}

function click(el) {
  el.dispatchEvent(new window.MouseEvent("click", { bubbles: true, cancelable: true }));
}

function key(name) {
  doc.dispatchEvent(new window.KeyboardEvent("keydown", { key: name, bubbles: true }));
}

function tick(ms = 20) {
  return new Promise((done) => setTimeout(done, ms));
}
