import { useEffect, useState } from "react";
import type { TocEntry } from "./PhaseToc";

/** The app's scroll container, per `App.tsx` — the window never scrolls. */
export const SCROLL_ROOT = "main-scroll";

/**
 * A section becomes current when its heading reaches reading position — the top
 * fifth of the viewport — rather than when it first peeks in from the bottom.
 */
const BAND = 0.2;

/**
 * Which section is being read, shared by the two things that need to say so: the
 * sticky rail on wide screens and the chip bar on narrow ones.
 *
 * One hook rather than one per navigator, because two implementations of "which
 * section am I in" would eventually disagree, and a table of contents pointing at
 * a different section than the bar above it is worse than having only one of them.
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
      const bandBottom = root.getBoundingClientRect().top + root.clientHeight * BAND;
      let current: string | undefined;
      for (const section of sections) {
        if (section.getBoundingClientRect().top <= bandBottom) current = section.id;
      }
      // Before the first heading crosses, the first section is still what is being
      // read; past the last one, `current` simply stops moving.
      setActive(current ?? sections[0]?.id ?? null);
    };

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
      observer.disconnect();
      root.removeEventListener("scroll", onScroll);
      if (frame) cancelAnimationFrame(frame);
    };
  }, [entries]);

  return active;
}

/** Scroll a section into reading position without leaving a fragment in the URL. */
export function goToSection(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
}
