import ArrowLeft02Icon from "@hugeicons/core-free-icons/ArrowLeft02Icon";
import { HugeiconsIcon } from "@hugeicons/react";
import { electives, electivesGate } from "../../data/electives";
import { InlineText } from "../../lib/markdown";
import { BlockList } from "../blocks/BlockList";
import { SectionHeading } from "../ui/SectionHeading";

const ACCENT = "#6B7280";

interface ElectivesViewProps {
  onNav: (view: string) => void;
}

export function ElectivesView({ onNav }: ElectivesViewProps) {
  return (
    <div className="max-w-[840px]">
      <header className="pt-2">
        <div className="mb-5 h-1 w-14 rounded-full border-b-2 border-dashed border-graphite" />
        <div className="mb-2 font-mono text-[11px] uppercase tracking-[0.18em] text-graphite">
          Optional · not part of your progress
        </div>
        <h1 className="text-[30px] font-bold leading-tight tracking-tight text-ink">
          Electives shelf
        </h1>
        <p className="mt-2 max-w-[60ch] text-[14px] italic text-graphite">
          Four specialisms that some GenAI jobs want and most don’t. Each one states the signal that
          makes it worth your time — and none of them counts toward finishing the course.
        </p>
      </header>

      <div className="mt-8 rounded-lg border-2 border-dashed border-line bg-card px-5 py-4">
        <h2 className="text-[15.5px] font-bold tracking-tight text-ink">{electivesGate.title}</h2>
        <BlockList blocks={electivesGate.blocks} accent={ACCENT} />
      </div>

      <SectionHeading
        kicker="Open one only if its trigger fires"
        title="The four electives"
        accent={ACCENT}
      />
      <div className="space-y-5">
        {electives.map((elective, i) => (
          <article
            key={elective.id}
            className="rounded-lg border border-line bg-card px-5 py-4 shadow-[0_1px_2px_rgba(0,0,0,0.03)]"
          >
            <div className="flex flex-wrap items-baseline gap-3">
              <span className="font-mono text-[11px] text-graphite">
                {String(i + 1).padStart(2, "0")}
              </span>
              <h3 className="text-[15.5px] font-bold tracking-tight text-ink">{elective.title}</h3>
              <span className="rounded bg-ink/[0.06] px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide text-graphite">
                {elective.tag}
              </span>
            </div>

            <dl className="mt-3 space-y-2 rounded-md border border-line bg-ink/[0.02] px-4 py-3">
              <div>
                <dt className="font-mono text-[9.5px] uppercase tracking-[0.16em] text-graphite">
                  Adoption trigger
                </dt>
                <dd className="mt-0.5 text-[13px] leading-relaxed text-ink/85">
                  <InlineText text={elective.trigger} />
                </dd>
              </div>
              <div>
                <dt className="font-mono text-[9.5px] uppercase tracking-[0.16em] text-graphite">
                  Honest cost
                </dt>
                <dd className="mt-0.5 text-[13px] leading-relaxed text-ink/85">
                  <InlineText text={elective.cost} />
                </dd>
              </div>
            </dl>

            <BlockList blocks={elective.blocks} accent={ACCENT} />

            <div className="mt-4 border-t border-line/60 pt-3">
              <div className="mb-2 font-mono text-[9.5px] uppercase tracking-[0.16em] text-graphite">
                Where to start
              </div>
              <ul className="space-y-1.5">
                {elective.resources.map((resource) => (
                  <li key={resource.url} className="flex items-baseline gap-2.5 text-[13px]">
                    <span className="shrink-0 font-mono text-[11px] text-graphite">→</span>
                    <a
                      href={resource.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-ink/85 underline decoration-line underline-offset-[3px] transition-colors hover:decoration-current"
                    >
                      {resource.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          </article>
        ))}
      </div>

      <div className="mt-12 mb-16 flex justify-end">
        <button
          type="button"
          onClick={() => onNav("dash")}
          className="flex items-center gap-2 rounded-md border border-line bg-card px-5 py-3 text-[13px] font-semibold text-ink transition-shadow hover:shadow-md"
        >
          <HugeiconsIcon icon={ArrowLeft02Icon} size={18} strokeWidth={2} />
          Back to the course — the nine phases are the job
        </button>
      </div>
    </div>
  );
}
