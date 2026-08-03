import type { ReactNode } from "react";

interface ScrollRegionProps {
  /** What the region holds, e.g. "Code sample" or "Table: retrieval trade-offs". */
  label: string;
  className?: string;
  children: ReactNode;
}

/**
 * A box that scrolls sideways and can be reached from the keyboard.
 *
 * A `div` with `overflow-x-auto` is scrollable with a mouse wheel or a trackpad
 * and by nothing else: it takes no focus, so a keyboard user tabbing through the
 * page skips it and never sees the half of the wide table or the long code line
 * that is off-screen. WCAG 2.1.1 counts that as content the keyboard cannot
 * reach, and axe reports it as `scrollable-region-focusable` — but only in a real
 * browser, because deciding it needs layout.
 *
 * `tabIndex={0}` makes it a tab stop, at which point the arrow keys scroll it.
 * A tab stop with no name announces itself as "group", so it carries a label
 * saying which table or which snippet this is. The focus ring is not decoration
 * either: a stop you cannot see is a stop that feels like the focus vanished.
 *
 * Not needed when the box already contains something focusable — a row of links
 * scrolls itself as you tab along it. `check-a11y.mjs` encodes exactly that: a
 * scroll container must either hold a focusable descendant or be one.
 */
export function ScrollRegion({ label, className = "", children }: ScrollRegionProps) {
  return (
    // `div role="group"`, not a labelled `section` and not `role="region"`.
    //
    // Both of those become landmarks once they carry a name, and the round-4
    // audit found what that costs at this scale: every code sample and every wide
    // table in the workbook comes through here, so a reader listing landmarks on
    // the deploy phase heard fourteen of them and had to walk the lot to find the
    // navigation. The note that used to be here argued the landmarks let you jump
    // between snippets — true, and not worth burying the page structure under,
    // because the section rail already navigates a phase by heading.
    //
    // `group` keeps the two things that matter and drops only the landmark: still
    // a tab stop, still announces its label. Removing either of those is what
    // re-breaks `scrollable-region-focusable`.
    // `useSemanticElements` wants a `<fieldset>` for this role and is switched off
    // for this file in `biome.json`: a fieldset groups form controls, brings a
    // legend and its own layout behaviour, and none of that describes a box that
    // holds a code sample.
    <div
      role="group"
      // biome-ignore lint/a11y/noNoninteractiveTabindex: a scroll container is the one non-interactive element that must be a tab stop — see above
      tabIndex={0}
      aria-label={label}
      className={`focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink ${className}`}
    >
      {children}
    </div>
  );
}
