import type { CalloutTone } from "../../data/types";
import { InlineText } from "../../lib/markdown";

const TONES: Record<CalloutTone, { label: string; color: string }> = {
  fix: { label: "MYTH, BUSTED", color: "var(--color-signal-red)" },
  tip: { label: "KEY IDEA", color: "var(--color-signal-green)" },
  warn: { label: "WATCH OUT", color: "var(--color-signal-amber)" },
};

interface CalloutProps {
  tone: CalloutTone;
  title: string;
  text: string;
}

export function Callout({ tone, title, text }: CalloutProps) {
  const { label, color } = TONES[tone];
  return (
    <div
      className="my-4 rounded-md border-l-[3px] px-4 py-3"
      style={{
        background: `color-mix(in oklab, ${color} 8%, transparent)`,
        borderColor: color,
      }}
    >
      <div className="mb-1 font-mono text-[11px] tracking-[0.14em]" style={{ color }}>
        {label}
      </div>
      <div className="mb-0.5 text-[13px] font-semibold text-ink">{title}</div>
      <div className="text-[13px] leading-relaxed text-ink/80">
        <InlineText text={text} />
      </div>
    </div>
  );
}
