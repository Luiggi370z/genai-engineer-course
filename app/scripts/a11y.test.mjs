import assert from "node:assert/strict";
import test from "node:test";
import { JSDOM } from "jsdom";
import {
  accentContrastFindings,
  accessibleName,
  focusables,
  keyboardFindings,
  navLabelFindings,
  scrollRegionFindings,
} from "./lib/a11y.mjs";
import { loadCourseData } from "./lib/load-data.mjs";

/**
 * The rules, each shown failing on the mistake it exists to catch and passing on
 * the fix. `check-a11y.mjs` runs them against the real page and currently reports
 * nothing — which is only worth believing if the rules can still fail, and a rule
 * that has never been seen red is a rule nobody has tested.
 */

/** A page with the bones every fixture needs, so each test states only its own bug. */
function page(body, { skip = true, main = true } = {}) {
  const skipLink = skip ? `<a href="#main" class="skip-link">Skip to content</a>` : "";
  const wrap = main ? `<main id="main" tabindex="-1">${body}</main>` : body;
  return new JSDOM(`<!doctype html><html><body>${skipLink}${wrap}</body></html>`).window.document;
}

const rules = (doc) => keyboardFindings(doc).map((f) => f.rule);

test("a clean page reports nothing", () => {
  const doc = page(`<button>Run the evals</button>`);
  assert.deepEqual(keyboardFindings(doc), []);
});

test("the skip link has to come first, or it has skipped nothing", () => {
  const doc = page(`<button>Menu</button>`, { skip: false });
  assert.ok(rules(doc).includes("skip-link"));
});

test("a skip link pointing at an id that is not there is caught", () => {
  const doc = new JSDOM(
    `<!doctype html><html><body><a href="#nowhere">Skip</a><main id="main" tabindex="-1"><button>Go</button></main></body></html>`,
  ).window.document;
  const finding = keyboardFindings(doc).find((f) => f.rule === "skip-link");
  assert.match(finding.message, /not on the page/);
});

test("a skip target that cannot take focus is caught", () => {
  // The subtle one: the anchor works, the page scrolls, and the next Tab starts
  // over from the top of the document because focus never moved.
  const doc = new JSDOM(
    `<!doctype html><html><body><a href="#main">Skip</a><main id="main"><button>Go</button></main></body></html>`,
  ).window.document;
  const finding = keyboardFindings(doc).find((f) => f.rule === "skip-link");
  assert.match(finding.message, /cannot take focus/);
});

test("a positive tabindex is a reordered queue, not a shortcut", () => {
  const doc = page(`<button tabindex="3">Later</button><button>Sooner</button>`);
  assert.ok(rules(doc).includes("tab-order"));
});

test("a control that announces nothing is caught", () => {
  const doc = page(`<button><svg></svg></button>`);
  const finding = keyboardFindings(doc).find((f) => f.rule === "named-controls");
  assert.match(finding.message, /announces nothing/);
});

test("aria-label and aria-labelledby both count as a name", () => {
  const doc = page(
    `<button aria-label="Close">×</button>` +
      `<span id="lbl">Import progress</span><input aria-labelledby="lbl">`,
  );
  assert.deepEqual(keyboardFindings(doc), []);
});

test("text content is a name, but only for the control that owns it", () => {
  const doc = page(`<button>Export</button>`);
  assert.equal(accessibleName(doc.querySelector("button")), "Export");
});

test("a focusable element inside aria-hidden is reachable by Tab and invisible to a reader", () => {
  const doc = page(`<div aria-hidden="true"><button>Ghost</button></div>`);
  assert.ok(rules(doc).includes("hidden-focusable"));
  // And it is excluded from the tab-stop list, so the name rule does not also fire
  // on it — one bug, one finding.
  assert.equal(focusables(doc).length, 1);
});

test("aria-expanded on something that is not a button does nothing on Space", () => {
  const doc = page(`<div aria-expanded="false" tabindex="0">Show the answer</div>`);
  assert.ok(rules(doc).includes("disclosure"));
});

test("an expanded disclosure whose panel is not there is caught", () => {
  const doc = page(`<button aria-expanded="true" aria-controls="panel">Hide</button>`);
  const finding = keyboardFindings(doc).find((f) => f.rule === "disclosure");
  assert.match(finding.message, /points at nothing/);
});

test("a collapsed disclosure may point at a panel that is not rendered yet", () => {
  // React unmounts the panel while closed, which is fine: nothing is announcing a
  // relationship to it until it opens.
  const doc = page(`<button aria-expanded="false" aria-controls="panel">Show</button>`);
  assert.deepEqual(keyboardFindings(doc), []);
});

test("two mains means the skip link has two destinations", () => {
  const doc = page(`<main id="second"><button>Go</button></main>`);
  assert.ok(rules(doc).includes("landmarks"));
});

test("a second nav has to be named, a lone one does not", () => {
  const lone = page(`<nav><a href="#main">Top</a></nav>`);
  assert.deepEqual(
    keyboardFindings(lone).filter((f) => f.rule === "landmarks"),
    [],
  );

  const pair = page(`<nav><a href="#main">Top</a></nav><nav><a href="#main">Also top</a></nav>`);
  assert.equal(keyboardFindings(pair).filter((f) => f.rule === "landmarks").length, 2);

  const named = page(
    `<nav aria-label="Phases"><a href="#main">Top</a></nav>` +
      `<nav aria-label="On this page"><a href="#main">Also top</a></nav>`,
  );
  assert.deepEqual(
    keyboardFindings(named).filter((f) => f.rule === "landmarks"),
    [],
  );
});

test("the nav label floor fails on the size the audit actually found", () => {
  const findings = navLabelFindings({
    "Sidebar.tsx": `<span className="font-mono text-[9px] uppercase">Optional</span>`,
  });
  assert.equal(findings.length, 1);
  assert.match(findings[0].subject, /Sidebar\.tsx:1$/);
  assert.match(findings[0].message, /below the 11px legibility floor/);
});

test("the floor passes at 11px and does not care about body copy elsewhere", () => {
  assert.deepEqual(
    navLabelFindings({ "Sidebar.tsx": `text-[11px] text-[12.5px] text-[30px]` }),
    [],
  );
});

test("every arbitrary size on a line is checked, not just the first", () => {
  const findings = navLabelFindings({
    "Toc.tsx": `<a className="text-[9.5px] sm:text-[10px]">Objectives</a>`,
  });
  assert.equal(findings.length, 2);
});

// --- accent contrast --------------------------------------------------------

const SURFACES = {
  light: { card: "#ffffff", paper: "#f6f7f4" },
  dark: { card: "#1c211f", paper: "#111413" },
};

test("the four accents the audit found unreadable would fail this rule", () => {
  // The pre-fix values, one accent per phase, drawn on both themes.
  const before = [
    { id: "p1", accent: { light: "#0E9F6E", dark: "#0E9F6E" } },
    { id: "p4", accent: { light: "#EA580C", dark: "#EA580C" } },
    { id: "p5", accent: { light: "#0891B2", dark: "#0891B2" } },
    { id: "p6", accent: { light: "#E11D48", dark: "#E11D48" } },
  ];
  const failed = new Set(
    accentContrastFindings(before, SURFACES).map((f) => f.subject.split("/")[0]),
  );
  assert.deepEqual([...failed].sort(), ["p1", "p4", "p5", "p6"]);
});

test("an accent is checked against the tint it is written on top of", () => {
  // Clears 4.5:1 on plain white and fails once the chip paints itself 12% under
  // the label. Catching only the first case is how the chips shipped unreadable.
  const phase = [{ id: "p9", accent: { light: "#0A7652", dark: "#7197EA" } }];
  const plain = { light: { card: "#ffffff" }, dark: { card: "#1c211f" } };
  assert.deepEqual(accentContrastFindings(phase, plain), []);
  const withPaper = { light: { paper: "#f6f7f4" }, dark: { card: "#1c211f" } };
  const findings = accentContrastFindings(phase, withPaper);
  assert.equal(findings.length, 1);
  assert.match(findings[0].message, /tinted 12%/);
});

test("a phase with no accent for a theme is a finding, not a crash", () => {
  const findings = accentContrastFindings([{ id: "p2", accent: { light: "#1556E4" } }], SURFACES);
  assert.equal(findings.length, 1);
  assert.equal(findings[0].subject, "p2/dark");
});

test("the shipped palette clears AA on both themes", async () => {
  const { phases } = await loadCourseData();
  assert.deepEqual(accentContrastFindings(phases, SURFACES), []);
});

// --- scroll regions ---------------------------------------------------------

test("a scrolling box with nothing focusable in it is unreachable", () => {
  const findings = scrollRegionFindings(page(`<div class="my-4 overflow-x-auto"><table/></div>`));
  assert.equal(findings.length, 1);
  assert.match(findings[0].message, /cannot be reached from a keyboard/);
});

test("a scrolling box that holds a link needs no tab stop of its own", () => {
  assert.deepEqual(
    scrollRegionFindings(page(`<div class="overflow-x-auto"><a href="#s1">Objectives</a></div>`)),
    [],
  );
});

test("a tab stop with no name announces as 'group', which is not a name", () => {
  const findings = scrollRegionFindings(
    page(`<div class="overflow-x-auto" tabindex="0" role="region"><table/></div>`),
  );
  assert.equal(findings.length, 1);
  assert.match(findings[0].message, /no accessible name/);
});

test("a named, focusable scroll region passes", () => {
  assert.deepEqual(
    scrollRegionFindings(
      page(
        `<div class="overflow-x-auto" tabindex="0" role="region" aria-label="Table: model">` +
          `<table/></div>`,
      ),
    ),
    [],
  );
});

test("the page's own scroller is exempt — the space bar already scrolls it", () => {
  assert.deepEqual(
    scrollRegionFindings(page(`<main id="main-scroll" class="overflow-y-auto" tabindex="-1"/>`)),
    [],
  );
});
