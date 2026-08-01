import { useEffect, useLayoutEffect, useRef, useState } from "react";

export interface TocEntry {
  id: string;
  label: string;
}

/** The app's scroll container, per `App.tsx` — the window never scrolls. */
const SCROLL_ROOT = "main-scroll";

interface Thumb {
  /** Pixels within the rail's own track — the same space the entries occupy. */
  top: number;
  height: number;
}

/**
 * Sticky rail listing the sections this phase actually has, with the current one
 * lit and a thumb marking it on the track.
 *
 * Deliberately *not* a second progress bar. The sidebar rings already mean "how much
 * of this have you completed", and a bar meaning "how far have you scrolled" beside
 * them would put two unrelated senses of progress on one screen — a student would
 * reasonably read scrolling to the bottom as finishing the phase.
 *
 * **The thumb is measured from the active row, not from `scrollTop`.** It used to be a
 * scrollbar — `scrollTop / scrollHeight` — which put it in a different coordinate space
 * from the track it is drawn on: the rail spaces entries evenly by list order, while
 * sections own wildly unequal amounts of document. In Phase 1, "Core concepts" is 61% of
 * the page but one seventh of the rail, so the thumb ran up to three rows ahead of the
 * lit entry. Deriving it from the row it points at makes the two agree by construction.
 *
 * Hidden below `xl` by the caller: on a narrow window it would either eat the reading
 * measure or float over the text, and a table of contents is not worth either.
 */
export function PhaseToc({ entries, accent }: { entries: TocEntry[]; accent: string }) {
  const [active, setActive] = useState<string | null>(entries[0]?.id ?? null);
  const [thumb, setThumb] = useState<Thumb>({ top: 0, height: 0 });
  const listRef = useRef<HTMLUListElement>(null);

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

  // Measured rather than computed: the thumb covers the active row, so it cannot
  // drift out of step with the highlight. Layout effect because it reads geometry —
  // doing it after paint would show the thumb at its old row for a frame.
  useLayoutEffect(() => {
    const list = listRef.current;
    if (!list) return;

    const place = () => {
      const index = entries.findIndex((entry) => entry.id === active);
      const row = index >= 0 ? (list.children[index] as HTMLElement | undefined) : undefined;
      if (row) setThumb({ top: row.offsetTop, height: row.offsetHeight });
    };

    place();

    // A label that wraps to two lines changes the row height under the thumb.
    const observer = new ResizeObserver(place);
    observer.observe(list);
    return () => observer.disconnect();
  }, [active, entries]);

  return (
    <nav aria-label="On this page" className="text-[11.5px]">
      <div className="mb-2.5 font-mono text-[9.5px] uppercase tracking-[0.16em] text-graphite">
        On this page
      </div>
      <div className="relative pl-3.5">
        <div className="absolute top-0 bottom-0 left-0 w-px bg-line" />
        <div
          className="absolute left-0 w-[3px] rounded-full transition-[top,height] duration-150"
          style={{ background: accent, top: thumb.top, height: thumb.height }}
        />
        <ul ref={listRef} className="space-y-2">
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
