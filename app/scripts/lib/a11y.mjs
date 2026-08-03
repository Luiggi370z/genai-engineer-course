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
 * Smallest type any label in the workbook is allowed to use, in px.
 *
 * Not a WCAG number — WCAG sets no minimum size, only a zoom requirement. It is a
 * legibility floor: the audit found labels at 9.5px, which is below the point
 * where the uppercase letterspaced mono this workbook uses for kickers stays
 * readable on a laptop panel, and those labels are the one part of the page a
 * reader cannot skip.
 *
 * It started as a rule about navigation chrome and now covers every rendered
 * component, because the 9.5px kickers the round-3 audit flagged were on
 * exercise cards and callouts, not in the nav.
 *
 * 11px until round 4, which read the same chrome on a laptop and asked for 12.
 * That is a legibility judgement rather than a measurement, and it is the reason
 * the floor is a constant: raising it moved 82 call sites and the argument only
 * had to be had once.
 */
export const MIN_NAV_LABEL_PX = 12;

/** WCAG AA for text below 18.66px bold / 24px regular — which is all of ours. */
export const MIN_CONTRAST = 4.5;

/**
 * The elements a screen reader offers in its landmark list.
 *
 * `section` is in here conditionally — it is only a landmark once it carries an
 * accessible name — so the caller filters it. `form` is left out for the same
 * reason and the workbook has none.
 */
const LANDMARKS =
  "main, [role='main'], nav, [role='navigation'], header, [role='banner'], " +
  "footer, [role='contentinfo'], aside, [role='complementary'], " +
  "section[aria-label], section[aria-labelledby], [role='region']";

/**
 * How many landmarks a view may offer before the list stops being useful.
 *
 * Not a WCAG number. A landmark list is a table of contents for the page, and a
 * table of contents with forty entries is a page with none — the round-4 audit
 * hit exactly that on the deploy phase. The workbook's real structure is a
 * banner, a main, three or four navs and the odd named region, so the cap sits
 * well above that and still well below one-per-block.
 */
export const MAX_LANDMARKS = 12;

export function focusables(doc) {
  return [...doc.querySelectorAll(FOCUSABLE)].filter((el) => !el.closest("[aria-hidden='true']"));
}

/**
 * Everything a screen reader would offer in its landmark list.
 *
 * A bare `section` is excluded because it is only a landmark once it has a name —
 * the selector asks for the named ones, and this drops any that slipped in
 * without one.
 */
export function landmarks(doc) {
  return [...doc.querySelectorAll(LANDMARKS)].filter(
    (el) =>
      !el.closest("[aria-hidden='true']") &&
      (el.tagName !== "SECTION" ||
        el.getAttribute("aria-label") ||
        el.getAttribute("aria-labelledby")),
  );
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
  // Landmarks describe the page, so there are a handful of them: banner, nav,
  // main, the odd named region. They are not a per-block device, and the round-4
  // audit found what happens when a repeated primitive becomes one — every code
  // sample and wide table on a phase was a labelled `section`, so the deploy
  // phase offered fourteen landmarks and the reader had to walk all of them to
  // find the navigation. The cap is loose on purpose: it is here to catch a
  // primitive that got promoted, not to police the page outline.
  const marks = landmarks(doc);
  if (marks.length > MAX_LANDMARKS) {
    const roles = new Map();
    for (const el of marks) {
      const role = el.getAttribute("role") ?? el.tagName.toLowerCase();
      roles.set(role, (roles.get(role) ?? 0) + 1);
    }
    const worst = [...roles].sort((a, b) => b[1] - a[1])[0];
    fail(
      "landmarks",
      "document",
      `${marks.length} landmarks, over the ${MAX_LANDMARKS} cap — ` +
        `${worst[1]} of them are '${worst[0]}'. A reader listing landmarks has to ` +
        "walk the lot; if one block primitive is repeating, make it role='group'",
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
 *
 * Two spellings, because for a while it only knew one. A Tailwind utility is how
 * a component sets type, and plain `font-size` is how the stylesheet does — and
 * the skip link, which is the first control on the page and the one a keyboard
 * user meets before anything else, is styled in the stylesheet. It sat at 11px
 * through a round of this gate reporting the floor was clean.
 */
export function navLabelFindings(sources, min = MIN_NAV_LABEL_PX, rule = "nav-label-size") {
  const out = [];
  const patterns = [/text-\[(\d+(?:\.\d+)?)px\]/g, /font-size:\s*(\d+(?:\.\d+)?)px/g];
  for (const [file, source] of Object.entries(sources)) {
    const lines = source.split("\n");
    lines.forEach((line, index) => {
      for (const pattern of patterns) {
        for (const match of line.matchAll(pattern)) {
          const px = Number(match[1]);
          if (px < min) {
            out.push({
              rule,
              subject: `${file}:${index + 1}`,
              message: `${match[0]} is below the ${min}px legibility floor`,
            });
          }
        }
      }
    });
  }
  return out;
}

/**
 * Motion that the reduced-motion preference cannot reach.
 *
 * `prefers-reduced-motion` is honoured in CSS by the reset in `index.css`, and
 * that reset is powerless over one thing: an explicit `behavior` passed to
 * `scrollIntoView` or `scrollTo` beats the `scroll-behavior` property, so a
 * hardcoded `"smooth"` animates a whole page of scrolling for a reader who asked
 * for none. The restored reading position is the worst case, because it fires on
 * load without being asked for.
 *
 * A literal is the whole tell. The one call site that scrolls on purpose now
 * reads the media query and passes `"auto"` or `"smooth"` accordingly, so any
 * literal reintroduced anywhere is the regression.
 */
export function motionFindings(sources, rule = "reduced-motion") {
  const out = [];
  for (const [file, source] of Object.entries(sources)) {
    source.split("\n").forEach((line, index) => {
      // Prose in a docblock explaining the rule is not a violation of it.
      if (/^\s*(\*|\/\/)/.test(line)) return;
      for (const match of line.matchAll(/behaviou?r:\s*["']smooth["']/g)) {
        out.push({
          rule,
          subject: `${file}:${index + 1}`,
          message:
            `${match[0]} is a literal — it overrides scroll-behavior and ignores ` +
            "prefers-reduced-motion; derive it from matchMedia instead",
        });
      }
    });
  }
  return out;
}

// --- colour -----------------------------------------------------------------

/** Relative luminance, WCAG 2.x definition. */
export function luminance(hex) {
  const channels = [1, 3, 5]
    .map((i) => Number.parseInt(hex.slice(i, i + 2), 16) / 255)
    .map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
}

/** Contrast ratio between two `#rrggbb` colours, 1:1 to 21:1. */
export function contrast(a, b) {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

/**
 * Every phase accent against the surfaces it is actually drawn on.
 *
 * This is the rule the round-3 audit stood in for: four accents rendered as 11px
 * labels below 4.5:1, found by a person reading hex codes. A colour is a datum
 * like any other, the backgrounds are two per theme, and the arithmetic is
 * twenty lines — so an auditor should never be the thing standing between a
 * hand-picked green and a student who cannot read it.
 *
 * The third surface is the one that is easy to forget: a phase chip paints the
 * accent at 12% over the card and then writes the *same accent* on top of it, so
 * the background moves toward the text and the ratio drops. That mix is checked
 * here in sRGB while the app renders it in oklab, which is close enough for a
 * gate — the browser tier measures the real thing.
 */
export function accentContrastFindings(phases, surfaces, min = MIN_CONTRAST) {
  const out = [];
  for (const phase of phases) {
    for (const [theme, backgrounds] of Object.entries(surfaces)) {
      const accent = phase.accent?.[theme];
      if (!accent) {
        out.push({
          rule: "accent-contrast",
          subject: `${phase.id}/${theme}`,
          message: "no accent declared for this theme",
        });
        continue;
      }
      const checks = Object.entries(backgrounds).flatMap(([name, bg]) => [
        [name, bg],
        [`${name} tinted 12% by the accent`, mix(accent, bg, 0.12)],
      ]);
      for (const [name, bg] of checks) {
        const ratio = contrast(accent, bg);
        if (ratio >= min) continue;
        out.push({
          rule: "accent-contrast",
          subject: `${phase.id}/${theme}`,
          message:
            `${accent} on ${name} (${bg}) is ${ratio.toFixed(2)}:1, below ${min}:1 — ` +
            "labels in this accent are 12px, so AA applies",
        });
      }
    }
  }
  return out;
}

/**
 * The white-on-accent foregrounds, as alpha over whatever is behind them.
 *
 * `text-white/85` is the subtitle and the eyebrow on the workshop header,
 * `text-white/90` is the chip text inside it, and plain white is the title.
 */
const ON_ACCENT = [
  ["white", 1],
  ["white/90", 0.9],
  ["white/85", 0.85],
];

/**
 * Reads `--accent-scrim` per theme out of the stylesheet.
 *
 * The scrim lives in `index.css` because that is where a theme becomes a palette.
 * Parsing it back out means this gate measures what ships: drop the scrim to 0 in
 * dark and the rule fails, which is the whole point of having it.
 */
export function scrimsFrom(css) {
  const out = {};
  for (const theme of ["light", "dark"]) {
    const block = new RegExp(`\\.${theme}\\s*\\{([^}]*)\\}`).exec(css);
    const declared = block && /--accent-scrim:\s*([\d.]+)%/.exec(block[1]);
    if (declared) out[theme] = Number(declared[1]) / 100;
  }
  return out;
}

/**
 * Contrast for the inverse job: the accent as a *fill* with white written on it.
 *
 * `accentContrastFindings` covers the accent as text. Three components fill a box
 * with it instead — the workshop header, the ladder chip on an exercise card, and
 * a selected answer button — and the dark accents are mid-tone, so white on them
 * lands near 2.5:1. The browser sweep only caught it once mobile folding brought
 * the workshop header within sampling range, which is late. This is the arithmetic
 * version, and it runs in milliseconds.
 */
export function accentFillFindings(phases, scrims, min = MIN_CONTRAST) {
  const out = [];
  for (const phase of phases) {
    for (const [theme, scrim] of Object.entries(scrims)) {
      const accent = phase.accent?.[theme];
      // A missing accent is already reported by accent-contrast.
      if (!accent) continue;
      const filled = mix("#000000", accent, scrim);
      const surfaces = [
        ["the filled accent", filled],
        ["the black/20 chip on it", mix("#000000", filled, 0.2)],
      ];
      for (const [where, bg] of surfaces) {
        for (const [label, alpha] of ON_ACCENT) {
          const ratio = contrast(mix("#ffffff", bg, alpha), bg);
          if (ratio >= min) continue;
          out.push({
            rule: "accent-fill",
            subject: `${phase.id}/${theme}`,
            message:
              `${label} on ${where} (${bg}, accent ${accent} at ${Math.round(scrim * 100)}% scrim) ` +
              `is ${ratio.toFixed(2)}:1, below ${min}:1 — raise --accent-scrim for .${theme}`,
          });
        }
      }
    }
  }
  return out;
}

function mix(a, b, amount) {
  const channel = (i) => {
    const av = Number.parseInt(a.slice(i, i + 2), 16);
    const bv = Number.parseInt(b.slice(i, i + 2), 16);
    return Math.round(av * amount + bv * (1 - amount))
      .toString(16)
      .padStart(2, "0");
  };
  return `#${channel(1)}${channel(3)}${channel(5)}`;
}

// --- scrolling --------------------------------------------------------------

/** The Tailwind utilities that turn a box into a scroll container. */
const SCROLLS = /\boverflow(-[xy])?-(auto|scroll)\b/;

/**
 * Scroll containers a keyboard can reach.
 *
 * A `div` with `overflow-x-auto` scrolls under a wheel or a trackpad and under
 * nothing else. Whatever sits past its right edge — the rest of a wide table,
 * the tail of a long line of Python — is then content a keyboard user cannot
 * get to, which is WCAG 2.1.1.
 *
 * There are two ways to be reachable and both are fine: hold something
 * focusable (a row of link chips scrolls itself as you tab along it), or *be*
 * focusable, which means `tabIndex=0` plus a name, because an unnamed tab stop
 * announces itself as "group" and tells the reader nothing.
 *
 * axe has this rule and cannot run it without layout, so it comes back
 * `incomplete` under jsdom and is silently dropped. This version asks the
 * question the other way round — every scroll container, whether or not it
 * happens to overflow at this width — which is stricter, deterministic, and
 * catches the box that only overflows on a phone.
 */
export function scrollRegionFindings(doc) {
  const out = [];
  for (const el of doc.querySelectorAll("*")) {
    const classes = typeof el.className === "string" ? el.className : "";
    if (!SCROLLS.test(classes)) continue;
    if (el.closest("[aria-hidden='true']")) continue;
    // The page scroller is the document's own scroll, driven by Page Up/Down
    // and the space bar wherever focus is; making it a tab stop would add a
    // stop that does nothing new.
    if (el.tagName === "MAIN" || el.id === "main-scroll") continue;
    if (el.querySelector(FOCUSABLE)) continue;

    const tabindex = el.getAttribute("tabindex");
    if (tabindex !== "0") {
      out.push({
        rule: "scroll-region",
        subject: describe(el),
        message:
          "scrolls but holds nothing focusable and is not a tab stop — its " +
          "off-screen content cannot be reached from a keyboard",
      });
      continue;
    }
    if (!accessibleName(el)) {
      out.push({
        rule: "scroll-region",
        subject: describe(el),
        message: "is a tab stop with no accessible name — it announces as 'group'",
      });
    }
  }
  return out;
}
