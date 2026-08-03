import type { Exercise, Mastery } from "../../data/types";

interface LadderRailProps {
  exercises: Exercise[];
  accent: string;
}

/** Ordered, so "the highest rung this phase reaches" is a max rather than a vote. */
const MASTERY: Mastery[] = ["understand", "implement", "integrate", "operate"];

const MEANS: Record<Mastery, string> = {
  understand: "you can explain it and defend the explanation",
  implement: "you built it, in isolation, and its tests are green",
  integrate: "you made it work across a seam you don’t control",
  operate: "you ran it under conditions that could hurt it, and have the numbers",
};

/**
 * Names the three rungs and says where each one lives in *this* phase.
 *
 * The ladder was always there — `after/` is the worked example, `before/` is the
 * faded one — but an unlabelled scaffold reads as a chore rather than as a stage
 * you are meant to leave behind. Rendered once per phase so the vocabulary is
 * available without nine copies of the same paragraph.
 */
export function LadderRail({ exercises, accent }: LadderRailProps) {
  const faded = exercises.filter((e) => e.rung === "faded").length;
  const independent = exercises.filter((e) => e.rung === "independent").length;
  const top = exercises.reduce<Mastery>(
    (best, e) => (MASTERY.indexOf(e.proves) > MASTERY.indexOf(best) ? e.proves : best),
    "understand",
  );

  const rungs = [
    {
      label: "Worked",
      count: "read it",
      where: "The code in the cards above, and each exercise’s `after/` reference",
    },
    {
      label: "Faded",
      count: `${faded} here`,
      where: "A `before/` scaffold with the judgement removed — the tests say when you’re done",
    },
    {
      label: "Independent",
      count: independent === 1 ? "1 here" : `${independent} here`,
      where: "Blank editor. No repo, no scaffold, no reference implementation to peek at",
    },
  ];

  return (
    <div className="mb-4 overflow-hidden rounded-lg border border-line bg-card">
      <div className="border-b border-line/60 px-4 py-2 font-mono text-[12px] uppercase tracking-[0.16em] text-graphite">
        The ladder · each rung takes away one more crutch
      </div>
      <div className="grid gap-px bg-line/40 sm:grid-cols-3">
        {rungs.map((rung, i) => (
          <div key={rung.label} className="bg-card px-4 py-3">
            <div className="flex items-baseline gap-2">
              <span className="font-mono text-[12px] text-graphite">{i + 1}</span>
              <span className="text-[12.5px] font-bold tracking-tight" style={{ color: accent }}>
                {rung.label}
              </span>
              <span className="font-mono text-[12px] text-graphite">{rung.count}</span>
            </div>
            <p className="mt-1 text-[12px] leading-[1.6] text-ink/70">
              {rung.where.split("`").map((part, j) =>
                j % 2 === 1 ? (
                  <code key={j} className="font-mono text-[12px] text-ink/85">
                    {part}
                  </code>
                ) : (
                  part
                ),
              )}
            </p>
          </div>
        ))}
      </div>
      <div className="border-t border-line/60 px-4 py-2.5">
        <p className="text-[12px] leading-[1.6] text-ink/70">
          <span className="font-semibold text-ink">A second, independent axis.</span> The rungs
          above say how much scaffolding a task removes. Each exercise also carries a{" "}
          <span className="font-mono text-[12px] text-ink/85">proves</span> chip saying what
          finishing it <em>demonstrates</em> — and the two come apart: a blank-editor task can still
          only prove you can build a thing in isolation. The highest this phase reaches is{" "}
          <span className="font-semibold" style={{ color: accent }}>
            {top}
          </span>
          , meaning {MEANS[top]}.
        </p>
      </div>
    </div>
  );
}
