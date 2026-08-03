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
 * A tab stop with no name announces itself as "group", so it carries
 * `role="region"` and a label saying which table or which snippet this is. The
 * focus ring is not decoration either: a stop you cannot see is a stop that feels
 * like the focus vanished.
 *
 * Not needed when the box already contains something focusable — a row of links
 * scrolls itself as you tab along it. `check-a11y.mjs` encodes exactly that: a
 * scroll container must either hold a focusable descendant or be one.
 */
export function ScrollRegion({ label, className = "", children }: ScrollRegionProps) {
  return (
    // A labelled `section` rather than `div role="region"`: same landmark, one
    // fewer ARIA attribute, and it means a reader listing landmarks can jump
    // between the code samples and tables of a phase.
    <section
      // biome-ignore lint/a11y/noNoninteractiveTabindex: a scroll container is the one non-interactive element that must be a tab stop — see above
      tabIndex={0}
      aria-label={label}
      className={`focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink ${className}`}
    >
      {children}
    </section>
  );
}
