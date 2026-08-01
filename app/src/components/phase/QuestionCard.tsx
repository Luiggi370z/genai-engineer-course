import MinusSignIcon from "@hugeicons/core-free-icons/MinusSignIcon";
import PlusSignIcon from "@hugeicons/core-free-icons/PlusSignIcon";
import { HugeiconsIcon } from "@hugeicons/react";
import { useState } from "react";
import type { QuestionAnswer } from "../../data/types";
import { InlineText } from "../../lib/markdown";
import type { Progress } from "../../lib/progress";

interface QuestionCardProps {
  q: QuestionAnswer;
  accent: string;
  progress: Progress;
  onToggle: (id: string) => void;
  /** Where a recall question came from, e.g. "Phase 03". Omitted for checkpoints. */
  source?: string;
}

/** Answer-first is the failure mode we want to avoid, so the answer starts hidden. */
export function QuestionCard({ q, accent, progress, onToggle, source }: QuestionCardProps) {
  const [open, setOpen] = useState(false);
  const known = !!progress[q.id];

  return (
    <div className="overflow-hidden rounded-md border border-line bg-card">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="flex w-full items-start gap-3 px-4 py-3 text-left hover:bg-ink/[0.03]"
      >
        <span
          className="mt-1 shrink-0 rounded px-1.5 py-0.5 font-mono text-[10px]"
          style={{
            background: known ? accent : "color-mix(in oklab, var(--color-ink) 8%, transparent)",
            color: known ? "#fff" : "var(--color-graphite)",
          }}
        >
          {known ? "GOT IT" : "Q"}
        </span>
        <span className="flex-1 text-[13.5px] font-medium leading-snug text-ink">
          <InlineText text={q.q} />
          {source && (
            <span className="ml-2 whitespace-nowrap font-mono text-[9.5px] uppercase tracking-[0.12em] text-graphite">
              ← {source}
            </span>
          )}
        </span>
        <span className="mt-1 text-graphite">
          <HugeiconsIcon icon={open ? MinusSignIcon : PlusSignIcon} size={13} strokeWidth={2.5} />
        </span>
      </button>
      {open && (
        <div className="border-t border-line/70 px-4 pt-1 pb-3.5">
          <p className="mb-3 text-[13px] leading-[1.7] text-ink/80">
            <InlineText text={q.a} />
          </p>
          <button
            type="button"
            onClick={() => onToggle(q.id)}
            className="rounded border px-2.5 py-1.5 font-mono text-[11px] transition-colors"
            style={
              known
                ? { borderColor: accent, color: accent, background: "transparent" }
                : { borderColor: accent, background: accent, color: "#fff" }
            }
          >
            {known ? "Mark as not learned" : "I could answer this cold"}
          </button>
        </div>
      )}
    </div>
  );
}
