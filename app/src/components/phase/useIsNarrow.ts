import { useEffect, useState } from "react";

/**
 * The `xl` breakpoint, where the phase layout changes shape.
 *
 * Above it the table-of-contents rail is on screen and the chip bar is hidden;
 * below it they swap. Kept as one string because it is the same 1280px Tailwind
 * uses in `PhaseView` and `SectionBar`, and two spellings of one breakpoint drift.
 */
const NARROW = "(max-width: 1279px)";

/**
 * Whether the viewport is narrow enough to be treated as mobile.
 *
 * Nearly everything responsive in this workbook is a Tailwind prefix, and that is
 * the right tool while the question is how something looks. This one is a
 * different question: whether a long section's content is *rendered at all*.
 * `hidden xl:block` would leave it in the DOM, which means a screen reader on a
 * phone still walks 12,000px of collapsed content and the tab order still stops
 * inside it — the collapse would be a visual lie.
 *
 * Defaults to false when `matchMedia` is missing, which is jsdom in the
 * accessibility gate. That is deliberate: false means "not narrow", so nothing
 * collapses and the gate scans the whole page. The collapsed state is covered
 * where it actually exists, in the Chromium sweep's 390px lane.
 */
export function useIsNarrow(): boolean {
  const [narrow, setNarrow] = useState(() => window.matchMedia?.(NARROW).matches ?? false);

  useEffect(() => {
    const query = window.matchMedia?.(NARROW);
    if (!query) return;
    const sync = () => setNarrow(query.matches);
    sync();
    query.addEventListener("change", sync);
    return () => query.removeEventListener("change", sync);
  }, []);

  return narrow;
}
