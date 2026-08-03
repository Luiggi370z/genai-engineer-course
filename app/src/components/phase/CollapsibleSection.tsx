import ArrowDown01Icon from "@hugeicons/core-free-icons/ArrowDown01Icon";
import { HugeiconsIcon } from "@hugeicons/react";
import type { ReactNode } from "react";
import { useDisclosure } from "../ui/Disclosure";
import { useIsNarrow } from "./useIsNarrow";

interface CollapsibleSectionProps {
  /** What the section holds, e.g. "8 cards". Read out on the trigger. */
  summary: string;
  /** The section's title, so the trigger names what it opens. */
  title: string;
  accent: string;
  /** False on short sections: renders the children and nothing else. */
  collapsible: boolean;
  children: ReactNode;
}

/**
 * A phase section a phone reader can fold away.
 *
 * The measurements behind this are in `lib/section-size.ts`; the short version is
 * that a phase runs 13,000-26,000px on a 390px viewport, which is 16 to 31
 * screens, and two sections are over half of it. The chip bar can already jump
 * between sections, and it is much less useful when every jump lands you in the
 * middle of another 12,000px of reading.
 *
 * Three things this deliberately does not do:
 *
 * **It does not move the anchor.** The heading stays mounted and keeps its id, so
 * `useActiveSection`'s sentinel is where it always was and both navigators keep
 * resolving their `#hrefs`. That is not just tidiness — the accessibility gate
 * fails if a table-of-contents entry points at an element that is not in the DOM,
 * and a collapse that unmounted the anchor would take the whole rail with it.
 *
 * **It does not collapse on a desktop.** Above `xl` there is no trigger at all,
 * not a trigger that happens to start open, because the rail is on screen there
 * and folding is a phone problem.
 *
 * **It does not animate the height.** A section is thousands of pixels tall; a
 * height transition on that is a long janky sweep, and `prefers-reduced-motion`
 * readers would have to be handled separately. The chevron turns and the content
 * appears.
 */
export function CollapsibleSection({
  summary,
  title,
  accent,
  collapsible,
  children,
}: CollapsibleSectionProps) {
  const narrow = useIsNarrow();
  const folded = narrow && collapsible;
  // Closed only where it is folded. Starting open everywhere would make this a
  // control that changes nothing until pressed, which is not what the audit asked
  // for; starting closed everywhere would fold a desktop that has no problem.
  // A reader who narrows an open desktop window keeps their content — the state
  // is theirs once the page has rendered, and re-hiding it would be a surprise.
  const { open, triggerProps, panelProps } = useDisclosure(!folded);

  if (!folded) return <>{children}</>;

  return (
    <>
      <button
        {...triggerProps}
        className="mb-3 flex w-full items-center gap-2 rounded-md border border-line bg-card px-3 py-2 text-left transition-colors hover:bg-ink/3"
      >
        <span
          className="transition-transform"
          style={{ color: accent, transform: open ? "rotate(0deg)" : "rotate(-90deg)" }}
        >
          <HugeiconsIcon icon={ArrowDown01Icon} size={16} strokeWidth={2} />
        </span>
        <span className="font-mono text-[12px] uppercase tracking-[0.12em] text-ink">
          {open ? "Hide" : "Show"} {title}
        </span>
        <span className="ml-auto font-mono text-[12px] text-graphite">{summary}</span>
      </button>
      {open && <div {...panelProps}>{children}</div>}
    </>
  );
}
