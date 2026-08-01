import EyeIcon from "@hugeicons/core-free-icons/EyeIcon";
import HelpCircleIcon from "@hugeicons/core-free-icons/HelpCircleIcon";
import { HugeiconsIcon } from "@hugeicons/react";
import { InlineText } from "../../lib/markdown";
import { useDisclosure } from "../ui/Disclosure";

interface PredictBlockProps {
  prompt: string;
  answer: string;
  consolidation: string;
  accent: string;
}

/**
 * Answer hidden, and hidden in a way that makes skipping feel like a choice.
 *
 * The effect being borrowed here is problem-solving-before-instruction: a wrong
 * guess you committed to makes the correction stick in a way that reading the
 * correct answer first does not. Which means the reveal button is not a
 * convenience — it is the whole mechanism, and it has to cost one click.
 *
 * `consolidation` renders *below* the answer and is required by the type, because
 * the evidence is unambiguous that an attempt without a follow-up teaching phase
 * buys nothing. A predict block that just says "gotcha" is worse than no block.
 */
export function PredictBlock({ prompt, answer, consolidation, accent }: PredictBlockProps) {
  const { open: revealed, triggerProps, panelProps } = useDisclosure();

  return (
    <div className="my-4 overflow-hidden rounded-md border-2 border-dashed border-line">
      <div className="px-4 py-3">
        <div
          className="mb-1.5 flex items-center gap-1.5 font-mono text-[10px] tracking-[0.14em]"
          style={{ color: accent }}
        >
          <HugeiconsIcon icon={HelpCircleIcon} size={12} strokeWidth={2.5} />
          PREDICT FIRST
        </div>
        <p className="text-[13px] leading-relaxed font-medium text-ink">
          <InlineText text={prompt} />
        </p>
        {/*
          One-way: once you have seen the answer, a button offering to hide it
          again would be pretending you can un-know it.
        */}
        {!revealed && (
          <button
            {...triggerProps}
            className="mt-2.5 inline-flex items-center gap-1.5 rounded border px-2.5 py-1.5 font-mono text-[11px] transition-colors"
            style={{ borderColor: accent, color: accent }}
          >
            <HugeiconsIcon icon={EyeIcon} size={12} strokeWidth={2.5} />
            I’ve committed to an answer — show me
          </button>
        )}
      </div>
      {revealed && (
        <div
          {...panelProps}
          className="border-t-2 border-dashed border-line bg-ink/[0.02] px-4 pt-3 pb-3.5"
        >
          <div className="mb-1 font-mono text-[9.5px] uppercase tracking-[0.16em] text-graphite">
            What actually happens
          </div>
          <p className="text-[13px] leading-relaxed text-ink/85">
            <InlineText text={answer} />
          </p>
          <div className="mt-3 border-t border-line/60 pt-2.5">
            <div className="mb-1 font-mono text-[9.5px] uppercase tracking-[0.16em] text-graphite">
              Why, and what to do with it
            </div>
            <p className="text-[13px] leading-relaxed text-ink/85">
              <InlineText text={consolidation} />
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
