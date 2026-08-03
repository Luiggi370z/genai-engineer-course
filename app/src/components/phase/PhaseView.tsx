import ArrowLeft02Icon from "@hugeicons/core-free-icons/ArrowLeft02Icon";
import ArrowRight02Icon from "@hugeicons/core-free-icons/ArrowRight02Icon";
import { HugeiconsIcon } from "@hugeicons/react";
import { useEffect, useMemo } from "react";
import { phases } from "../../data/phases";
import type { Phase } from "../../data/types";
import { accentOf } from "../../lib/accent";
import { InlineText } from "../../lib/markdown";
import type { Progress } from "../../lib/progress";
import { readingMinutes } from "../../lib/reading-time";
import { isLongSection } from "../../lib/section-size";
import { BlockList } from "../blocks/BlockList";
import { CheckItem } from "../ui/CheckItem";
import { SectionHeading } from "../ui/SectionHeading";
import { CollapsibleSection } from "./CollapsibleSection";
import { ExerciseCard } from "./ExerciseCard";
import { LadderRail } from "./LadderRail";
import { PhaseToc, type TocEntry } from "./PhaseToc";
import { QuestionCard } from "./QuestionCard";
import { SectionBar } from "./SectionBar";
import { useActiveSection } from "./useActiveSection";
import { WorkshopCard } from "./WorkshopCard";

interface PhaseViewProps {
  phase: Phase;
  progress: Progress;
  onToggle: (id: string) => void;
  onNav: (view: string) => void;
  /** Reports the section being read, so the app can remember the place. */
  onSection: (sectionId: string) => void;
  nextPhase?: Phase | undefined;
}

/**
 * Which phase an objective belongs to, so a recall question can say where it is
 * reaching back to. Derived rather than authored: phase numbers come from the
 * order in `phases/index.ts`, so hard-coding one here would go stale the next
 * time a phase is inserted.
 */
function sourceOf(objectiveId: string): string {
  const owner = phases.find((p) => p.objectives.some((o) => o.id === objectiveId));
  return owner ? `Phase ${String(owner.num).padStart(2, "0")}` : "earlier";
}

/**
 * The table of contents, derived from the sections this phase actually has rather
 * than a fixed list — most of them are optional, and an entry pointing at nothing
 * would be worse than no entry.
 */
function tocEntries(phase: Phase): TocEntry[] {
  const entries: TocEntry[] = [{ id: "objectives", label: "Learning objectives" }];
  if (phase.recall?.length) entries.push({ id: "recall", label: "Warm-up" });
  entries.push({ id: "concepts", label: "Core concepts" });
  if (phase.example) entries.push({ id: "example", label: "Worked example" });
  entries.push({ id: "exercises", label: "Exercises" });
  if (phase.workshop) entries.push({ id: "workshop", label: "Workshop" });
  if (phase.checkpoint?.length) entries.push({ id: "checkpoint", label: "Checkpoint" });
  if (phase.qbank?.length) entries.push({ id: "qbank", label: "Question bank" });
  entries.push({ id: "resources", label: "Resources" });
  return entries;
}

export function PhaseView({
  phase,
  progress,
  onToggle,
  onNav,
  onSection,
  nextPhase,
}: PhaseViewProps) {
  const accent = accentOf(phase.id);
  const minutes = readingMinutes(phase);
  const entries = useMemo(() => tocEntries(phase), [phase]);
  const active = useActiveSection(entries);

  useEffect(() => {
    if (active) onSection(active);
  }, [active, onSection]);

  return (
    <div className="flex gap-10">
      <div className="min-w-0 max-w-[840px] flex-1">
        <header className="pt-2">
          <div className="mb-5 h-1 w-14 rounded-full" style={{ background: accent }} />
          <div
            className="mb-2 font-mono text-[12px] uppercase tracking-[0.18em]"
            style={{ color: accent }}
          >
            Phase {String(phase.num).padStart(2, "0")} · {phase.weeks}
          </div>
          <h1 className="text-[30px] font-bold leading-tight tracking-tight text-ink">
            {phase.title}
          </h1>
          <p className="mt-2 max-w-[60ch] text-[14px] italic text-graphite">
            <InlineText text={phase.tagline} />
          </p>
          <div
            className="mt-5 max-w-[68ch] rounded-lg border border-l-[3px] px-4 py-3"
            style={{
              background: `color-mix(in oklab, ${accent} 6%, transparent)`,
              borderColor: `color-mix(in oklab, ${accent} 22%, transparent)`,
              borderLeftColor: accent,
            }}
          >
            <div className="mb-1.5 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
              <span
                className="font-mono text-[12px] uppercase tracking-[0.16em]"
                style={{ color: accent }}
              >
                The 60-second version
              </span>
              {/*
              The second half of this label is not padding. "~9 min" on a phase that
              runs a fortnight would read as the time the phase takes, which is the
              exact misconception the course spends nine phases attacking.
            */}
              <span className="font-mono text-[12px] text-graphite">
                ~{minutes} min to read — the work itself runs {phase.weeks}
              </span>
            </div>
            <p className="text-[13.5px] leading-[1.7] text-ink/85">
              <InlineText text={phase.tldr} />
            </p>
          </div>
          {/*
            Repeated on every phase rather than said once on the dashboard, because
            it is not information — it is an instruction, and the moment it applies
            is the moment you open a lesson with a reference implementation sitting
            one directory away.
          */}
          <p className="mt-3 max-w-[68ch] text-[12.5px] leading-[1.65] text-graphite">
            <span className="font-medium text-ink/75">Attempt before you read.</span> Every lesson
            ships a <code className="font-mono text-[12px]">before/</code> you write and an{" "}
            <code className="font-mono text-[12px]">after/</code> that already works. Open the
            reference only once your own attempt runs or you are genuinely stuck, and diff it
            against what you wrote. Reading a working solution feels like learning and mostly is
            not: the struggle you skip is the part that makes it stick, and a solution you have read
            is indistinguishable, to you, from one you could have written.
          </p>
        </header>

        {/* The sticky rail's counterpart below `xl`, where the rail is hidden. Placed
            after the header rather than above it: a navigator is only useful once you
            know what you are navigating, and the first thing on a phase should be its
            title. */}
        <SectionBar entries={entries} accent={accent} active={active} />

        <SectionHeading
          id="objectives"
          kicker="What you'll walk away able to do"
          title="Learning objectives"
          accent={accent}
        />
        <div className="divide-y divide-line/50 rounded-lg border border-line bg-card py-1.5">
          {phase.objectives.map((o) => (
            <CheckItem
              key={o.id}
              id={o.id}
              text={o.text}
              checked={!!progress[o.id]}
              onToggle={onToggle}
              accent={accent}
            />
          ))}
        </div>

        {phase.recall && phase.recall.length > 0 && (
          <>
            <SectionHeading
              id="recall"
              kicker="Before you read anything new — no notes, no scrolling back"
              title="Warm-up: three from earlier"
              accent={accent}
            />
            <p className="mb-3 max-w-[62ch] text-[13px] leading-relaxed text-graphite">
              Getting one wrong here is the most useful thing that can happen to you today. These
              reach back deliberately far — the gap between recognising an answer and producing one
              is invisible until something asks you to produce one.
            </p>
            <div className="space-y-2.5">
              {phase.recall.map((r) => (
                <QuestionCard
                  key={r.id}
                  q={r}
                  accent={accent}
                  progress={progress}
                  onToggle={onToggle}
                  source={sourceOf(r.from)}
                />
              ))}
            </div>
          </>
        )}

        <SectionHeading
          id="concepts"
          kicker="The ideas, kept short"
          title="Core concepts"
          accent={accent}
        />
        <CollapsibleSection
          title="Core concepts"
          summary={`${phase.concepts.length} cards`}
          accent={accent}
          collapsible={isLongSection(phase, "concepts")}
        >
          <div className="space-y-5">
            {phase.concepts.map((concept, i) => (
              <article
                key={concept.id}
                // Stable per-card anchor. The id is already unique course-wide (the
                // integrity gate enforces it) and it is what `scripts/screenshot.mjs`
                // navigates to when it photographs each block kind.
                id={concept.id}
                className="rounded-lg border border-line bg-card px-5 py-4 shadow-[0_1px_2px_rgba(0,0,0,0.03)]"
              >
                <div className="flex flex-wrap items-baseline gap-3">
                  <span className="font-mono text-[12px]" style={{ color: accent }}>
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <h3 className="text-[15.5px] font-bold tracking-tight text-ink">
                    {concept.title}
                  </h3>
                  {concept.tag && (
                    <span
                      className="rounded px-1.5 py-0.5 font-mono text-[12px] uppercase tracking-wide"
                      style={{
                        background: `color-mix(in oklab, ${accent} 12%, transparent)`,
                        color: accent,
                      }}
                    >
                      {concept.tag}
                    </span>
                  )}
                </div>
                <BlockList blocks={concept.blocks} accent={accent} />
              </article>
            ))}
          </div>
        </CollapsibleSection>

        {phase.example && (
          <div
            id="example"
            className="mt-6 scroll-mt-6 rounded-lg border px-5 py-4"
            style={{
              background: `color-mix(in oklab, ${accent} 7%, transparent)`,
              borderColor: `color-mix(in oklab, ${accent} 25%, transparent)`,
            }}
          >
            <div
              className="mb-1.5 font-mono text-[12px] uppercase tracking-[0.16em]"
              style={{ color: accent }}
            >
              {phase.example.title}
            </div>
            <p className="text-[13.5px] leading-[1.7] text-ink/85">
              <InlineText text={phase.example.text} />
            </p>
          </div>
        )}

        <SectionHeading
          id="exercises"
          kicker="Hands on — worked, then faded, then blank"
          title="Exercises"
          accent={accent}
        />
        <CollapsibleSection
          title="Exercises"
          summary={`${phase.exercises.length} exercises`}
          accent={accent}
          collapsible={isLongSection(phase, "exercises")}
        >
          <LadderRail exercises={phase.exercises} accent={accent} />
          <div className="space-y-3">
            {phase.exercises.map((exercise, i) => (
              <ExerciseCard
                key={exercise.id}
                exercise={exercise}
                index={i}
                done={!!progress[exercise.id]}
                onToggle={onToggle}
                accent={accent}
              />
            ))}
          </div>
        </CollapsibleSection>

        {phase.workshop && (
          // The anchor stays outside the collapse, always mounted: the chip bar
          // and the rail both link to `#workshop`, and the a11y gate fails a link
          // that points at nothing.
          <div id="workshop" className="scroll-mt-6">
            <CollapsibleSection
              title="Workshop"
              summary={`${phase.workshop.deliverables.length} deliverables`}
              accent={accent}
              collapsible={isLongSection(phase, "workshop")}
            >
              <WorkshopCard
                workshop={phase.workshop}
                progress={progress}
                onToggle={onToggle}
                accent={accent}
              />
            </CollapsibleSection>
          </div>
        )}

        {phase.checkpoint && phase.checkpoint.length > 0 && (
          <>
            <SectionHeading
              id="checkpoint"
              kicker="Say it out loud before you peek"
              title="Checkpoint"
              accent={accent}
            />
            <p className="mb-3 max-w-[68ch] text-[13px] leading-[1.7] text-graphite">
              Each question lists what a complete answer has to name. That is the line between
              describing a system and defending one: what else you could have built, what ruled the
              others out, what measurement says it worked, and where it breaks. The last is the one
              nearly everyone leaves out, which is why it is printed rather than hoped for.
            </p>
            <div className="space-y-2.5">
              {phase.checkpoint.map((q) => (
                <QuestionCard
                  key={q.id}
                  q={q}
                  accent={accent}
                  progress={progress}
                  onToggle={onToggle}
                />
              ))}
            </div>
          </>
        )}

        {phase.qbank && (
          <>
            <SectionHeading
              id="qbank"
              kicker="Your drill deck — five a day, out loud, no notes"
              title="Interview question bank"
              accent={accent}
            />
            <CollapsibleSection
              title="the question bank"
              summary={`${phase.qbank.reduce((n, g) => n + g.items.length, 0)} questions`}
              accent={accent}
              collapsible={isLongSection(phase, "qbank")}
            >
              <div className="space-y-6">
                {phase.qbank.map((group) => (
                  <div key={group.group}>
                    <div className="mb-2 font-mono text-[12px] uppercase tracking-[0.14em] text-graphite">
                      {group.group}
                    </div>
                    <div className="space-y-2">
                      {group.items.map((q) => (
                        <QuestionCard
                          key={q.id}
                          q={q}
                          accent={accent}
                          progress={progress}
                          onToggle={onToggle}
                        />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </CollapsibleSection>
          </>
        )}

        <SectionHeading
          id="resources"
          kicker="Curated, with links — not a link dump"
          title="Resources"
          accent={accent}
        />
        <ul className="space-y-2 rounded-lg border border-line bg-card px-5 py-4">
          {phase.resources.map((resource, i) => (
            <li
              key={resource.url}
              className="flex items-baseline gap-2.5 text-[13px] leading-relaxed"
            >
              <span className="shrink-0 font-mono text-[12px]" style={{ color: accent }}>
                {String(i + 1).padStart(2, "0")}
              </span>
              <a
                href={resource.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-ink/85 underline decoration-line underline-offset-[3px] transition-colors hover:decoration-current"
              >
                {resource.label}
              </a>
              <span className="hidden truncate font-mono text-[12px] text-graphite sm:inline">
                {resource.url.replace(/^https?:\/\//, "").split("/")[0]}
              </span>
            </li>
          ))}
        </ul>

        <div className="mt-12 mb-16 flex justify-end">
          {nextPhase ? (
            <button
              type="button"
              onClick={() => onNav(nextPhase.id)}
              className="group flex items-center gap-3 rounded-md border bg-card px-5 py-3 transition-shadow hover:shadow-md"
              style={{
                borderColor: `color-mix(in oklab, ${accentOf(nextPhase.id)} 40%, transparent)`,
              }}
            >
              <div className="text-left">
                <div
                  className="font-mono text-[12px] uppercase tracking-[0.14em]"
                  style={{ color: accentOf(nextPhase.id) }}
                >
                  Next · Phase {String(nextPhase.num).padStart(2, "0")}
                </div>
                <div className="text-[14px] font-semibold text-ink">{nextPhase.title}</div>
              </div>
              <span
                className="transition-transform group-hover:translate-x-0.5"
                style={{ color: accentOf(nextPhase.id) }}
              >
                <HugeiconsIcon icon={ArrowRight02Icon} size={20} strokeWidth={2} />
              </span>
            </button>
          ) : (
            <button
              type="button"
              onClick={() => onNav("dash")}
              className="flex items-center gap-2 rounded-md border border-line bg-card px-5 py-3 text-[13px] font-semibold text-ink transition-shadow hover:shadow-md"
            >
              <HugeiconsIcon icon={ArrowLeft02Icon} size={18} strokeWidth={2} />
              Back to the dashboard — keep the daily reps going
            </button>
          )}
        </div>
      </div>

      {/* A plain div, not an `aside`: the sidebar is already a complementary
          landmark, and two unnamed ones read identically to a screen reader
          listing regions. The `nav` inside carries the label that matters. */}
      <div className="sticky top-2 hidden h-fit w-[190px] shrink-0 self-start pt-2 xl:block">
        <PhaseToc entries={entries} accent={accent} active={active} />
      </div>
    </div>
  );
}
