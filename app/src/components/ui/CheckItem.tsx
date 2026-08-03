import Tick02Icon from "@hugeicons/core-free-icons/Tick02Icon";
import { HugeiconsIcon } from "@hugeicons/react";
import { InlineText } from "../../lib/markdown";

interface CheckItemProps {
  id: string;
  text: string;
  checked: boolean;
  onToggle: (id: string) => void;
  accent: string;
}

/** The one checkbox row used by prerequisites, objectives and deliverables. */
export function CheckItem({ id, text, checked, onToggle, accent }: CheckItemProps) {
  return (
    <button
      type="button"
      onClick={() => onToggle(id)}
      aria-pressed={checked}
      className="group flex w-full items-start gap-3 rounded-md px-3 py-2.5 text-left transition-colors hover:bg-ink/4"
    >
      <span
        className="mt-0.5 flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded-[5px] border-2 transition-colors"
        style={{
          borderColor: checked ? accent : "var(--color-line)",
          background: checked ? accent : "transparent",
        }}
      >
        {checked && (
          <HugeiconsIcon icon={Tick02Icon} size={12} strokeWidth={3} className="text-white" />
        )}
      </span>
      <span
        className={`text-[13.5px] leading-relaxed ${
          checked ? "text-graphite line-through decoration-ink/20" : "text-ink/90"
        }`}
      >
        <InlineText text={text} />
      </span>
    </button>
  );
}
