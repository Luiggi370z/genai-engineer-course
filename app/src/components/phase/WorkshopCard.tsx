import type { Workshop } from "../../data/types";
import { formatWorkshopEffort, summarizeEffort } from "../../lib/effort";
import { InlineText } from "../../lib/markdown";
import type { Progress } from "../../lib/progress";
import { BlockList } from "../blocks/BlockList";
import { CheckItem } from "../ui/CheckItem";

interface WorkshopCardProps {
  workshop: Workshop;
  progress: Progress;
  onToggle: (id: string) => void;
  accent: string;
}

const TIER = {
  minimum: {
    heading: "Minimum — the walking skeleton",
    blurb:
      "The smallest version that is really the thing. If this week is the week it does not fit, ship these and stop here; that is a stopping point, not quitting.",
  },
  full: {
    heading: "Full — the version you show people",
    blurb: "Everything above, plus the parts that make it defensible rather than demoable.",
  },
} as const;

export function WorkshopCard({ workshop, progress, onToggle, accent }: WorkshopCardProps) {
  const shipped = workshop.deliverables.filter((d) => progress[d.id]).length;
  const minimum = workshop.deliverables.filter((d) => d.tier === "minimum");
  const done = minimum.every((d) => progress[d.id]);

  return (
    <div className="mt-12">
      <div
        className="overflow-hidden rounded-xl border-2 shadow-sm"
        style={{ borderColor: accent }}
      >
        <div className="px-5 py-4" style={{ background: accent }}>
          <div className="font-mono text-[11px] uppercase tracking-[0.18em] text-white/85">
            Capstone workshop · build it end to end
          </div>
          <div className="mt-1 text-[18px] font-bold text-white">{workshop.title}</div>
          <div className="mt-1 text-[13px] leading-snug text-white/85">
            <InlineText text={workshop.subtitle} />
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <span className="rounded bg-black/20 px-2 py-0.5 font-mono text-[11px] text-white/90">
              repo: {workshop.repo}
            </span>
            {/* Hours, not minutes — the thing to know before starting one of
                these on a weeknight. Kept equal to the brief by the gate. */}
            <span
              className="rounded bg-black/20 px-2 py-0.5 font-mono text-[11px] text-white/90"
              title={formatWorkshopEffort(workshop.effort)}
            >
              {summarizeEffort(workshop.effort)}
            </span>
            <span className="rounded bg-black/20 px-2 py-0.5 font-mono text-[11px] text-white/90">
              brief: {workshop.doc}
            </span>
            <span className="rounded bg-black/20 px-2 py-0.5 font-mono text-[11px] text-white/90">
              {shipped}/{workshop.deliverables.length} deliverables
            </span>
            {/* The milestone worth celebrating, and the one a flat progress bar hides. */}
            <span className="rounded bg-black/20 px-2 py-0.5 font-mono text-[11px] text-white/90">
              {done
                ? "minimum shipped"
                : `minimum: ${minimum.filter((d) => progress[d.id]).length}/${minimum.length}`}
            </span>
          </div>
        </div>
        <div className="bg-card px-5 py-4">
          <BlockList blocks={workshop.blocks} accent={accent} />
          {(["minimum", "full"] as const).map((tier) => {
            const items = workshop.deliverables.filter((d) => d.tier === tier);
            if (!items.length) return null;
            return (
              <div key={tier}>
                <div
                  className="mt-5 font-mono text-[11px] uppercase tracking-[0.14em]"
                  style={{ color: accent }}
                >
                  {TIER[tier].heading}
                </div>
                <p className="mt-1 mb-2 max-w-[68ch] text-[12.5px] leading-relaxed text-graphite">
                  {TIER[tier].blurb}
                </p>
                <div className="divide-y divide-line/50 rounded-lg border border-line py-1">
                  {items.map((d) => (
                    <CheckItem
                      key={d.id}
                      id={d.id}
                      text={d.text}
                      checked={!!progress[d.id]}
                      onToggle={onToggle}
                      accent={accent}
                    />
                  ))}
                </div>
              </div>
            );
          })}
          {workshop.stretch && (
            <div className="mt-4">
              <div className="mb-2 font-mono text-[11px] uppercase tracking-[0.14em] text-graphite">
                Stretch — only if the full pass came easily
              </div>
              <ul className="space-y-1.5">
                {workshop.stretch.map((goal, i) => (
                  <li key={i} className="flex gap-2 text-[12.5px] leading-relaxed text-ink/75">
                    <span className="shrink-0 font-mono" style={{ color: accent }}>
                      +
                    </span>
                    <span>
                      <InlineText text={goal} />
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
