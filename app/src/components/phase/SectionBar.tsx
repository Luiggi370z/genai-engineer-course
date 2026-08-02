import { useEffect, useRef } from "react";
import type { TocEntry } from "./PhaseToc";
import { goToSection, useActiveSection } from "./useActiveSection";

/**
 * The narrow-screen half of the table of contents: one sticky row of chips that
 * scrolls sideways, with the current section lit.
 *
 * `PhaseToc` is hidden below `xl` because a sticky rail on a narrow window either
 * eats the reading measure or floats over the text. That left every screen under
 * 1280px with no way to see the shape of a phase, and phases run long — a student
 * on a laptop had to scroll the whole page to discover there was a workshop in it.
 *
 * A row of chips instead of a collapsed rail: it costs one line, it survives being
 * only 320px wide by scrolling rather than wrapping to four rows, and the active
 * chip scrolls itself into view, so the bar always shows where you are plus what is
 * on either side. That last part is the whole point — a navigator that shows only
 * the current section is a label, not a navigator.
 */
export function SectionBar({ entries, accent }: { entries: TocEntry[]; accent: string }) {
  const active = useActiveSection(entries);
  const listRef = useRef<HTMLDivElement>(null);

  // Keep the lit chip on screen as the page scrolls under it. `nearest` rather than
  // `center` so a chip already visible does not shunt the row sideways on every
  // section change — motion the reader did not ask for reads as a glitch.
  useEffect(() => {
    const row = listRef.current;
    if (!row || !active) return;
    const chip = row.querySelector<HTMLElement>(`[data-section="${CSS.escape(active)}"]`);
    chip?.scrollIntoView({ block: "nearest", inline: "nearest" });
  }, [active]);

  return (
    <nav
      aria-label="Sections in this phase"
      className="sticky top-0 z-20 -mx-5 mb-6 border-b border-line bg-paper/95 backdrop-blur sm:-mx-8 xl:hidden"
    >
      <div
        ref={listRef}
        className="flex gap-1.5 overflow-x-auto px-5 py-2 [scrollbar-width:none] sm:px-8 [&::-webkit-scrollbar]:hidden"
      >
        {entries.map((entry) => {
          const current = active === entry.id;
          return (
            <a
              key={entry.id}
              href={`#${entry.id}`}
              data-section={entry.id}
              aria-current={current ? "location" : undefined}
              onClick={(event) => {
                event.preventDefault();
                goToSection(entry.id);
              }}
              className={`shrink-0 whitespace-nowrap rounded-full border px-3 py-1 text-[12px] leading-normal transition-colors ${
                current ? "font-semibold" : "border-line text-graphite hover:bg-ink/[0.04]"
              }`}
              style={
                current
                  ? {
                      color: accent,
                      borderColor: `color-mix(in oklab, ${accent} 45%, transparent)`,
                      background: `color-mix(in oklab, ${accent} 10%, transparent)`,
                    }
                  : undefined
              }
            >
              {entry.label}
            </a>
          );
        })}
      </div>
    </nav>
  );
}
