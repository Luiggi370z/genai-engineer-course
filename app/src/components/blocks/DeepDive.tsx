import ArrowRight01Icon from "@hugeicons/core-free-icons/ArrowRight01Icon";
import { HugeiconsIcon } from "@hugeicons/react";
import type { Block } from "../../data/types";
import { useDisclosure } from "../ui/Disclosure";
import { BlockList } from "./BlockList";

interface DeepDiveProps {
  title: string;
  blocks: Block[];
  accent: string;
}

/**
 * The optional tail of a card, collapsed by default.
 *
 * This is the instrument for meeting the density budget: material that is true
 * and useful but not needed on the first pass moves in here instead of being
 * deleted. Its contents do not count against the card's visible prose cap, which
 * is exactly why the checker limits one per card and caps what fits inside —
 * otherwise "collapse it" becomes permission to keep writing.
 *
 * The chrome says *aside*, not *task*: a quiet inline row rather than the dashed
 * border of a predict block, so a skipped deep dive costs the student nothing but
 * a skipped prediction still feels like ducking the question.
 */
export function DeepDive({ title, blocks, accent }: DeepDiveProps) {
  const { open, triggerProps, panelProps } = useDisclosure();

  return (
    <div
      className="my-4 rounded-md border border-line/80 bg-ink/[0.015]"
      style={open ? { borderColor: `color-mix(in oklab, ${accent} 35%, transparent)` } : undefined}
    >
      <button
        {...triggerProps}
        className="flex w-full items-center gap-2 px-3.5 py-2.5 text-left hover:bg-ink/[0.03]"
      >
        <span
          className="shrink-0 transition-transform duration-150"
          style={{ color: accent, transform: open ? "rotate(90deg)" : undefined }}
        >
          <HugeiconsIcon icon={ArrowRight01Icon} size={14} strokeWidth={2.5} />
        </span>
        <span
          className="font-mono text-[12px] uppercase tracking-[0.16em]"
          style={{ color: accent }}
        >
          Deep dive
        </span>
        <span className="flex-1 text-[12.5px] font-medium leading-snug text-ink/80">{title}</span>
        <span className="shrink-0 font-mono text-[12px] uppercase tracking-[0.12em] text-graphite">
          {open ? "Hide" : "Optional"}
        </span>
      </button>
      {open && (
        <div {...panelProps} className="border-t border-line/70 px-3.5 pt-0.5 pb-2.5">
          <BlockList blocks={blocks} accent={accent} />
        </div>
      )}
    </div>
  );
}
