import { useEffect, useState } from "react";
import type { TocEntry } from "./PhaseToc";

/** The app's scroll container, per `App.tsx` — the window never scrolls. */
export const SCROLL_ROOT = "main-scroll";

/**
 * A section becomes current when its heading reaches reading position — the top
 * fifth of the viewport — rather than when it first peeks in from the bottom.
 *
 * An upper bound rather than the figure used: `syncActive` shrinks it when the
 * sections on the page are shorter than it is, which is what a folded phone page
 * produces.
 */
const BAND = 0.2;

/**
 * The section the reader last asked for by name, rather than by scrolling.
 *
 * Module state because the two sides of it are a module function and a hook, and
 * threading a callback from `goToSection` through `PhaseToc`, `SectionBar` and the
 * resume path in `App.tsx` would put four copies of this in the tree to express
 * one fact. Only ever consulted at the bottom of the page, where the layout stops
 * distinguishing between the last few sections.
 */
let requested: string | null = null;

/** The mounted `syncActive`, so a request can recompute without a scroll event. */
const resyncs = new Set<() => void>();

/**
 * Which section is being read.
 *
 * Called once, by `PhaseView`, and handed down to the three things that need the
 * answer: the sticky rail on wide screens, the chip bar on narrow ones, and the
 * saved reading position. It used to be called once per navigator — two
 * implementations of "which section am I in" eventually disagree, and a table of
 * contents pointing somewhere other than the bar above it is worse than having
 * only one of them.
 */
export function useActiveSection(entries: TocEntry[]): string | null {
  const [active, setActive] = useState<string | null>(entries[0]?.id ?? null);

  useEffect(() => {
    const root = document.getElementById(SCROLL_ROOT);
    if (!root) return;
    const sections = entries
      .map((entry) => document.getElementById(entry.id))
      .filter((el): el is HTMLElement => el !== null);
    if (sections.length === 0) return;

    const syncActive = () => {
      const rootTop = root.getBoundingClientRect().top;
      const measured = sections.map((section) => ({
        id: section.id,
        top: section.getBoundingClientRect().top - rootTop,
      }));

      // The band, but never taller than half the shortest section on the page.
      //
      // A section shorter than the band cannot be selected at all: the rule below
      // takes the last heading above the band, so a heading that sits inside the
      // band alongside its neighbour always loses to that neighbour. Unfolded that
      // never happens, because sections run to thousands of pixels. Fold the long
      // ones on a phone and the headings land 84-133px apart against a 159px band,
      // at which point tapping "Exercises" highlighted "Workshop" — the table of
      // contents disagreeing with the page, which is the class of bug 7bf0e2f
      // already fixed once from the other direction.
      //
      // Capping globally rather than per section is the part that matters. A
      // per-section cap still lets the *next* section, if it is long, claim the
      // full band and win.
      const gaps = measured
        .slice(1)
        .map((section, i) => section.top - (measured[i]?.top ?? section.top));
      const shortest = gaps.length ? Math.min(...gaps) : Number.POSITIVE_INFINITY;
      const band = Math.min(root.clientHeight * BAND, shortest / 2);

      // The bottom of the page is the one place geometry cannot answer.
      //
      // Scrolling stops there, so the last few headings sit on screen below the
      // band and none of them can ever reach it — and, worse, every one of them
      // produces the *same* scroll position. Ask for the question bank or ask for
      // the resources on a folded phase 9 and the page ends up identical, so no
      // rule reading position can tell which one you wanted. Nothing here is a
      // measurement problem; the information is simply not in the layout.
      //
      // So the request wins, and only here. `requested` is cleared the moment the
      // page is not at the bottom, which is any real scrolling — so a reader who
      // arrives at the end by scrolling gets the last section, and one who asked
      // for a particular section gets the one they asked for.
      if (root.scrollTop + root.clientHeight >= root.scrollHeight - 2) {
        const asked = requested && measured.some((section) => section.id === requested);
        setActive(asked ? requested : (sections[sections.length - 1]?.id ?? null));
        return;
      }
      requested = null;

      let current: string | undefined;
      for (const section of measured) {
        if (section.top <= band) current = section.id;
      }
      // Before the first heading crosses, the first section is still what is being
      // read; past the last one, `current` simply stops moving.
      setActive(current ?? sections[0]?.id ?? null);
    };

    resyncs.add(syncActive);

    const observer = new IntersectionObserver(syncActive, {
      root,
      rootMargin: `0px 0px -${(1 - BAND) * 100}% 0px`,
    });
    for (const section of sections) observer.observe(section);

    let frame = 0;
    const onScroll = () => {
      if (frame) return;
      frame = requestAnimationFrame(() => {
        frame = 0;
        syncActive();
      });
    };

    onScroll();
    root.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      resyncs.delete(syncActive);
      observer.disconnect();
      root.removeEventListener("scroll", onScroll);
      if (frame) cancelAnimationFrame(frame);
    };
  }, [entries]);

  return active;
}

/**
 * Scroll a section into reading position without leaving a fragment in the URL.
 *
 * The CSS reset in `index.css` cannot reach this one: an explicit `behavior`
 * passed to `scrollIntoView` beats the `scroll-behavior` property, so a reader
 * who asked for no motion still got a long animated sweep down the page — worst
 * on the restored reading position, which fires unprompted at load.
 */
export function goToSection(id: string) {
  const target = document.getElementById(id);
  if (!target) return;
  requested = id;
  const behavior = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches
    ? "auto"
    : "smooth";
  target.scrollIntoView({ behavior });
  // Asking for a section while the page is already at the bottom moves nothing, so
  // no scroll event arrives and the answer would stay on the previous section.
  for (const resync of resyncs) resync();
}
