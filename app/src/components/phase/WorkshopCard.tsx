import type { Workshop } from "../../data/types";
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

export function WorkshopCard({ workshop, progress, onToggle, accent }: WorkshopCardProps) {
  const shipped = workshop.deliverables.filter((d) => progress[d.id]).length;

  return (
    <div className="mt-12">
      <div
        className="overflow-hidden rounded-xl border-2 shadow-sm"
        style={{ borderColor: accent }}
      >
        <div className="px-5 py-4" style={{ background: accent }}>
          <div className="font-mono text-[10.5px] uppercase tracking-[0.18em] text-white/85">
            Capstone workshop · build it end to end
          </div>
          <div className="mt-1 text-[18px] font-bold text-white">{workshop.title}</div>
          <div className="mt-1 text-[13px] leading-snug text-white/85">
            <InlineText text={workshop.subtitle} />
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <span className="rounded bg-black/20 px-2 py-0.5 font-mono text-[10.5px] text-white/90">
              repo: {workshop.repo}
            </span>
            <span className="rounded bg-black/20 px-2 py-0.5 font-mono text-[10.5px] text-white/90">
              {shipped}/{workshop.deliverables.length} deliverables
            </span>
          </div>
        </div>
        <div className="bg-card px-5 py-4">
          <BlockList blocks={workshop.blocks} accent={accent} />
          <div
            className="mt-5 mb-2 font-mono text-[10.5px] uppercase tracking-[0.14em]"
            style={{ color: accent }}
          >
            Acceptance criteria — check them off as you ship
          </div>
          <div className="divide-y divide-line/50 rounded-lg border border-line py-1">
            {workshop.deliverables.map((d) => (
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
          {workshop.stretch && (
            <div className="mt-4">
              <div className="mb-2 font-mono text-[10.5px] uppercase tracking-[0.14em] text-graphite">
                Stretch goals
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
