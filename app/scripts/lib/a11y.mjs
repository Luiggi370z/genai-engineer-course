/**
 * Accessibility rules the workbook is held to, as pure functions over a DOM.
 *
 * axe covers the rules a machine can decide from markup alone, and `check-a11y.mjs`
 * runs it. What axe cannot check is the thing this workbook is most likely to get
 * wrong: whether you can *drive* it from the keyboard. A page can pass every axe
 * rule while the mobile nav swallows focus, the skip link points at nothing, and a
 * disclosure never announces that it opened.
 *
 * So these are the keyboard-journey rules, written against a `Document` so they can
 * be unit-tested on a five-line fixture as well as run against the built page.
 */

/** Everything the browser will stop on, in document order. */
const FOCUSABLE =
  "a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), " +
  "textarea:not([disabled]), [tabindex]:not([tabindex='-1'])";

/**
 * Smallest type the navigation chrome is allowed to use, in px.
 *
 * Not a WCAG number — WCAG sets no minimum size, only a zoom requirement. It is a
 * legibility floor: the audit found nav labels at 9px, which is below the point
 * where the uppercase letterspaced mono this workbook uses for kickers stays
 * readable on a laptop panel, and those labels are the one part of the page a
 * reader cannot skip.
 */
export const MIN_NAV_LABEL_PX = 11;

export function focusables(doc) {
  return [...doc.querySelectorAll(FOCUSABLE)].filter((el) => !el.closest("[aria-hidden='true']"));
}

/**
 * The accessible name, close enough for a gate.
 *
 * Deliberately not a full accname implementation: this only has to answer "would a
 * screen reader read out something, or nothing", and the false-negative direction
 * is the safe one — a control this calls unnamed is a control worth looking at.
 */
export function accessibleName(el) {
  const labelled = el.getAttribute("aria-labelledby");
  if (labelled) {
    const text = labelled
      .split(/\s+/)
      .map((id) => el.ownerDocument.getElementById(id)?.textContent ?? "")
      .join(" ")
      .trim();
    if (text) return text;
  }
  const attr = (name) => (el.getAttribute(name) ?? "").trim();
  return (
    attr("aria-label") ||
    (el.textContent ?? "").trim() ||
    attr("title") ||
    attr("alt") ||
    el.querySelector("img[alt]")?.getAttribute("alt")?.trim() ||
    (el.tagName === "INPUT" && el.type === "submit" ? attr("value") : "") ||
    ""
  );
}

function describe(el) {
  const id = el.id ? `#${el.id}` : "";
  const cls =
    el.className && typeof el.className === "string" ? `.${el.className.split(/\s+/)[0]}` : "";
  return `${el.tagName.toLowerCase()}${id}${cls}`;
}

/**
 * Every keyboard rule, run in one pass. Returns findings rather than throwing, so
 * a run reports all of them instead of the first.
 */
export function keyboardFindings(doc) {
  const out = [];
  const fail = (rule, subject, message) => out.push({ rule, subject, message });
  const stops = focusables(doc);

  // --- the skip link ---------------------------------------------------------
  // First stop, or it is not a skip link — a skip link you reach after the nav has
  // skipped nothing. And it must land somewhere focusable, or the next Tab starts
  // from the top of the document again, which is the exact trap it exists to avoid.
  const first = stops[0];
  if (!first) {
    fail(
      "skip-link",
      "document",
      "no focusable element at all — the page cannot be driven by keyboard",
    );
  } else if (first.tagName !== "A" || !(first.getAttribute("href") ?? "").startsWith("#")) {
    fail(
      "skip-link",
      describe(first),
      "the first stop is not a skip link to a fragment on this page",
    );
  } else {
    const target = doc.getElementById(first.getAttribute("href").slice(1));
    if (!target) {
      fail(
        "skip-link",
        describe(first),
        `points at ${first.getAttribute("href")}, which is not on the page`,
      );
    } else if (!target.matches(FOCUSABLE) && target.getAttribute("tabindex") !== "-1") {
      fail(
        "skip-link",
        describe(target),
        "the skip target cannot take focus — give it tabindex='-1' so the next Tab continues from here",
      );
    }
  }

  // --- tab order -------------------------------------------------------------
  for (const el of stops) {
    if (Number(el.getAttribute("tabindex") ?? 0) > 0) {
      fail(
        "tab-order",
        describe(el),
        "positive tabindex jumps the queue and reorders every stop after it",
      );
    }
  }

  // --- names -----------------------------------------------------------------
  for (const el of stops) {
    if (!accessibleName(el)) {
      fail("named-controls", describe(el), "focusable but announces nothing");
    }
  }

  // --- nothing focusable inside hidden content -------------------------------
  for (const el of doc.querySelectorAll("[aria-hidden='true']")) {
    for (const inner of el.querySelectorAll(FOCUSABLE)) {
      fail(
        "hidden-focusable",
        describe(inner),
        "focusable, but inside aria-hidden — reachable by Tab, invisible to a reader",
      );
    }
  }

  // --- disclosures -----------------------------------------------------------
  for (const el of doc.querySelectorAll("[aria-expanded]")) {
    const role = el.getAttribute("role");
    if (el.tagName !== "BUTTON" && el.tagName !== "A" && role !== "button") {
      fail(
        "disclosure",
        describe(el),
        "carries aria-expanded but is not a button, so Space and Enter do nothing",
      );
    }
    const controls = el.getAttribute("aria-controls");
    if (el.getAttribute("aria-expanded") === "true" && controls && !doc.getElementById(controls)) {
      fail(
        "disclosure",
        describe(el),
        `is expanded but aria-controls="${controls}" points at nothing`,
      );
    }
  }

  // --- landmarks -------------------------------------------------------------
  const mains = doc.querySelectorAll("main, [role='main']");
  if (mains.length !== 1) {
    fail(
      "landmarks",
      "document",
      `${mains.length} main landmarks — a skip link needs exactly one destination`,
    );
  }
  const navs = [...doc.querySelectorAll("nav, [role='navigation']")];
  if (navs.length > 1) {
    for (const nav of navs) {
      // Text content deliberately does not count here: a landmark is named by its
      // label, not by everything inside it, and every nav has links in it.
      const named = nav.getAttribute("aria-label") || nav.getAttribute("aria-labelledby");
      if (!named) {
        fail(
          "landmarks",
          describe(nav),
          "one of several navs and unnamed — a reader listing landmarks hears 'navigation' twice",
        );
      }
    }
  }

  return out;
}

/**
 * The type-size floor for navigation chrome, read off the source rather than the
 * DOM.
 *
 * A computed-style check would be better and is not available: the workbook ships
 * as one file whose styles are Tailwind v4 output, and jsdom drops most of it while
 * parsing, so every element computes to the 16px default. Scanning the arbitrary
 * `text-[Npx]` utilities in the handful of files that *are* the navigation is
 * narrower but honest — it fails on exactly the mistake it is meant to catch.
 */
export function navLabelFindings(sources, min = MIN_NAV_LABEL_PX) {
  const out = [];
  for (const [file, source] of Object.entries(sources)) {
    const lines = source.split("\n");
    lines.forEach((line, index) => {
      for (const match of line.matchAll(/text-\[(\d+(?:\.\d+)?)px\]/g)) {
        const px = Number(match[1]);
        if (px < min) {
          out.push({
            rule: "nav-label-size",
            subject: `${file}:${index + 1}`,
            message: `${match[0]} is below the ${min}px floor for navigation chrome`,
          });
        }
      }
    });
  }
  return out;
}
