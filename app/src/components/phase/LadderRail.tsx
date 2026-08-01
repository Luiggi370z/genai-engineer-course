import type { Exercise } from "../../data/types";

interface LadderRailProps {
  exercises: Exercise[];
  accent: string;
}

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
      <div className="border-b border-line/60 px-4 py-2 font-mono text-[9.5px] uppercase tracking-[0.16em] text-graphite">
        The ladder · each rung takes away one more crutch
      </div>
      <div className="grid gap-px bg-line/40 sm:grid-cols-3">
        {rungs.map((rung, i) => (
          <div key={rung.label} className="bg-card px-4 py-3">
            <div className="flex items-baseline gap-2">
              <span className="font-mono text-[10px] text-graphite">{i + 1}</span>
              <span className="text-[12.5px] font-bold tracking-tight" style={{ color: accent }}>
                {rung.label}
              </span>
              <span className="font-mono text-[9.5px] text-graphite">{rung.count}</span>
            </div>
            <p className="mt-1 text-[12px] leading-[1.6] text-ink/70">
              {rung.where.split("`").map((part, j) =>
                j % 2 === 1 ? (
                  <code key={j} className="font-mono text-[11px] text-ink/85">
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
    </div>
  );
}
