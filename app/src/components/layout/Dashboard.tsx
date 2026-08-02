import { dashboard } from "../../data/dashboard";
import { milestones, myths, outOfScope, prerequisites } from "../../data/intro";
import { phases } from "../../data/phases";
import { InlineText } from "../../lib/markdown";
import type { Progress } from "../../lib/progress";
import { CheckItem } from "../ui/CheckItem";
import { ProgressRing } from "../ui/ProgressRing";
import { ManifestPanel } from "./ManifestPanel";

interface DashboardProps {
  progress: Progress;
  onToggle: (id: string) => void;
  onNav: (view: string) => void;
  phasePct: (phaseId: string) => number;
  overallPct: number;
}

function SectionLabel({ kicker, title, tone }: { kicker: string; title: string; tone?: string }) {
  return (
    <>
      <div
        className="mb-1 font-mono text-[10.5px] uppercase tracking-[0.16em]"
        style={{ color: tone ?? "var(--color-graphite)" }}
      >
        {kicker}
      </div>
      <h2 className="mb-4 text-[19px] font-bold tracking-tight text-ink">{title}</h2>
    </>
  );
}

export function Dashboard({ progress, onToggle, onNav, phasePct, overallPct }: DashboardProps) {
  const workshopCount = phases.filter((p) => p.workshop).length;

  return (
    <div className="max-w-[840px]">
      <header className="pt-2 pb-2">
        <div className="mb-3 font-mono text-[11px] uppercase tracking-[0.2em] text-graphite">
          Self-paced · {phases.length} phases · {workshopCount} workshops · {dashboard.refreshed}
        </div>
        <h1 className="max-w-[24ch] text-[34px] font-bold leading-[1.12] tracking-tight text-ink">
          {dashboard.title}
        </h1>
        <p className="mt-3 max-w-[62ch] text-[14.5px] leading-relaxed text-ink/75">
          {dashboard.intro}
          <strong className="font-semibold">{dashboard.introEmphasis}</strong>
        </p>
        <div className="mt-5 flex items-center gap-3">
          <ProgressRing pct={overallPct} color="var(--color-ink)" size={40} />
          <div>
            <div className="text-[20px] font-bold leading-none text-ink">
              {Math.round(overallPct * 100)}%
            </div>
            <div className="mt-0.5 font-mono text-[10.5px] tracking-wide text-graphite">
              {dashboard.progressCaption}
            </div>
          </div>
        </div>
      </header>

      <div className="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-2">
        {phases.map((phase) => (
          <button
            type="button"
            key={phase.id}
            onClick={() => onNav(phase.id)}
            className="rounded-lg border bg-card px-4 py-3.5 text-left transition-shadow hover:shadow-md"
            style={{
              borderColor: `color-mix(in oklab, ${phase.color} 27%, transparent)`,
              borderTopWidth: 3,
              borderTopColor: phase.color,
            }}
          >
            <div className="flex items-center justify-between gap-2">
              <span
                className="font-mono text-[10.5px] uppercase tracking-[0.16em]"
                style={{ color: phase.color }}
              >
                Phase {String(phase.num).padStart(2, "0")} · {phase.weeks}
              </span>
              <ProgressRing pct={phasePct(phase.id)} color={phase.color} size={26} />
            </div>
            <div className="mt-1.5 text-[15px] font-bold tracking-tight text-ink">
              {phase.title}
            </div>
            <div className="mt-1 line-clamp-2 text-[12px] leading-snug text-graphite">
              <InlineText text={phase.tagline} />
            </div>
          </button>
        ))}
      </div>

      <section className="mt-12">
        <SectionLabel kicker="The loop you'll repeat" title="How this course works" />
        <div className="space-y-2.5 rounded-lg border border-line bg-card px-5 py-4">
          {dashboard.loop.map((item) => (
            <div key={item.step} className="flex gap-3 text-[13.5px] leading-relaxed text-ink/85">
              <span className="mt-0.5 shrink-0 font-mono text-[11px] text-graphite">
                {item.step}
              </span>
              <span>
                <InlineText text={item.text} />
              </span>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-12">
        <SectionLabel
          kicker="Fact-checked, not transcribed"
          title="Four myths this course retires"
          tone="var(--color-signal-red)"
        />
        <div className="space-y-3">
          {myths.map((myth) => (
            <div
              key={myth.title}
              className="rounded-md border border-line border-l-[3px] border-l-signal-red bg-card px-4 py-3"
            >
              <div className="text-[13.5px] font-semibold text-ink">{myth.title}</div>
              <p className="mt-1 text-[13px] leading-[1.7] text-ink/75">
                <InlineText text={myth.text} />
              </p>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-12">
        <SectionLabel
          kicker="Read this before Phase 1, not after Phase 9"
          title="What this course does not teach"
        />
        <p className="mb-3 max-w-[68ch] text-[13px] leading-[1.7] text-ink/75">
          This is a course about <strong>building systems on top of models</strong>. Everything
          below is deliberately out of scope — none of it is needed for that job, and all of it is
          needed for a different one. Saying so up front beats leaving you to infer the boundary
          from an absence.
        </p>
        <div className="divide-y divide-line/60 rounded-lg border border-line bg-card">
          {outOfScope.map((item) => (
            <div key={item.topic} className="px-4 py-3">
              <div className="text-[13px] font-semibold text-ink">{item.topic}</div>
              <p className="mt-1 text-[12.5px] leading-[1.7] text-ink/75">
                <InlineText text={item.why} />
              </p>
              <p className="mt-1 text-[12px] leading-relaxed text-graphite">
                Start here instead: <InlineText text={item.next} />
              </p>
            </div>
          ))}
        </div>
      </section>

      <ManifestPanel phases={phases} progress={progress} />

      <section className="mt-12">
        <SectionLabel kicker="Quick self-check before Phase 1" title="Prerequisites" />
        <div className="divide-y divide-line/50 rounded-lg border border-line bg-card py-1.5">
          {prerequisites.map((item) => (
            <CheckItem
              key={item.id}
              id={item.id}
              text={item.text}
              checked={!!progress[item.id]}
              onToggle={onToggle}
              accent="var(--color-ink)"
            />
          ))}
        </div>
      </section>

      <section className="mt-12 mb-16">
        <SectionLabel kicker="Gates, not dates" title="Move on when you clear the bar" />
        <div className="divide-y divide-line/60 rounded-lg border border-line bg-card">
          {milestones.map((milestone, i) => (
            <div key={milestone.stage} className="flex gap-4 px-4 py-3">
              <span className="mt-0.5 w-6 shrink-0 font-mono text-[11px] text-graphite">
                G{i + 1}
              </span>
              <div>
                <div className="text-[13px] font-semibold text-ink">
                  <InlineText text={milestone.stage} />
                </div>
                <p className="mt-0.5 text-[12.5px] leading-relaxed text-ink/70">
                  <InlineText text={milestone.bar} />
                </p>
              </div>
            </div>
          ))}
        </div>
        <p className="mt-4 max-w-[68ch] text-[12px] leading-relaxed text-graphite">
          {dashboard.honestyNote}
        </p>
      </section>
    </div>
  );
}
