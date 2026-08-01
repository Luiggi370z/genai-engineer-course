import { useEffect, useState } from "react";

export interface TocEntry {
  id: string;
  label: string;
}

/** The app's scroll container, per `App.tsx` — the window never scrolls. */
const SCROLL_ROOT = "main-scroll";

interface Thumb {
  /** Fraction of the page above the viewport, and the fraction it covers. */
  offset: number;
  size: number;
}

/**
 * Sticky rail listing the sections this phase actually has, with the current one
 * lit and a thumb showing where in the page you are.
 *
 * Deliberately *not* a second progress bar. The sidebar rings already mean "how much
 * of this have you completed", and a bar meaning "how far have you scrolled" beside
 * them would put two unrelated senses of progress on one screen — a student would
 * reasonably read scrolling to the bottom as finishing the phase. A thumb on the
 * rail's own track can only be about this page.
 *
 * Hidden below `xl` by the caller: on a narrow window it would either eat the reading
 * measure or float over the text, and a table of contents is not worth either.
 */
export function PhaseToc({ entries, accent }: { entries: TocEntry[]; accent: string }) {
  const [active, setActive] = useState<string | null>(entries[0]?.id ?? null);
  const [thumb, setThumb] = useState<Thumb>({ offset: 0, size: 1 });

  useEffect(() => {
    const root = document.getElementById(SCROLL_ROOT);
    if (!root) return;
    const sections = entries
      .map((entry) => document.getElementById(entry.id))
      .filter((el): el is HTMLElement => el !== null);
    if (sections.length === 0) return;

    // A section becomes current when its heading reaches reading position — the top
    // fifth of the viewport — rather than when it first peeks in from the bottom.
    const BAND = 0.2;

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
        setThumb({
          offset: root.scrollTop / root.scrollHeight,
          size: root.clientHeight / root.scrollHeight,
        });
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

  return (
    <nav aria-label="On this page" className="text-[11.5px]">
      <div className="mb-2.5 font-mono text-[9.5px] uppercase tracking-[0.16em] text-graphite">
        On this page
      </div>
      <div className="relative pl-3.5">
        <div className="absolute top-0 bottom-0 left-0 w-px bg-line" />
        <div
          className="absolute left-0 w-[3px] rounded-full transition-[top] duration-100"
          style={{
            background: accent,
            top: `${thumb.offset * 100}%`,
            height: `${Math.max(thumb.size * 100, 6)}%`,
          }}
        />
        <ul className="space-y-2">
          {entries.map((entry) => (
            <li key={entry.id}>
              <a
                href={`#${entry.id}`}
                onClick={(event) => {
                  // Keeps the URL clean — the app has no hash routing, so a lingering
                  // fragment would only be a trap on reload.
                  event.preventDefault();
                  document.getElementById(entry.id)?.scrollIntoView({ behavior: "smooth" });
                }}
                className="block leading-snug transition-colors"
                style={
                  active === entry.id
                    ? { color: accent, fontWeight: 600 }
                    : { color: "var(--color-graphite)" }
                }
              >
                {entry.label}
              </a>
            </li>
          ))}
        </ul>
      </div>
    </nav>
  );
}
