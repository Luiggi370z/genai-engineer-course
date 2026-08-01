import MinusSignIcon from "@hugeicons/core-free-icons/MinusSignIcon";
import PlusSignIcon from "@hugeicons/core-free-icons/PlusSignIcon";
import Tick02Icon from "@hugeicons/core-free-icons/Tick02Icon";
import { HugeiconsIcon } from "@hugeicons/react";
import { useState } from "react";
import type { Exercise } from "../../data/types";
import { InlineText } from "../../lib/markdown";
import { CodeBlock } from "../blocks/CodeBlock";

interface ExerciseCardProps {
  exercise: Exercise;
  index: number;
  done: boolean;
  onToggle: (id: string) => void;
  accent: string;
}

export function ExerciseCard({ exercise, index, done, onToggle, accent }: ExerciseCardProps) {
  const [showSolution, setShowSolution] = useState(false);
  const blank = exercise.rung === "independent";

  return (
    <div
      className={`overflow-hidden rounded-lg bg-card ${
        blank ? "border-2 border-dashed" : "border border-line"
      }`}
      style={blank ? { borderColor: `color-mix(in oklab, ${accent} 45%, transparent)` } : undefined}
    >
      <div className="flex items-start gap-3 px-4 py-3.5">
        <button
          type="button"
          onClick={() => onToggle(exercise.id)}
          aria-label={`Mark exercise ${index + 1} complete`}
          aria-pressed={done}
          className="mt-0.5 flex h-[20px] w-[20px] shrink-0 items-center justify-center rounded-full border-2"
          style={{
            borderColor: done ? accent : "var(--color-line)",
            background: done ? accent : "transparent",
          }}
        >
          {done && (
            <HugeiconsIcon icon={Tick02Icon} size={12} strokeWidth={3} className="text-white" />
          )}
        </button>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-baseline gap-2">
            <span className="font-mono text-[11px] text-graphite">EX.{index + 1}</span>
            <h4 className={`text-[14px] font-semibold ${done ? "text-graphite" : "text-ink"}`}>
              {exercise.title}
            </h4>
            <span
              className="rounded px-1.5 py-0.5 font-mono text-[9.5px] uppercase tracking-wide"
              style={
                blank
                  ? { background: accent, color: "#fff" }
                  : {
                      background: `color-mix(in oklab, ${accent} 12%, transparent)`,
                      color: accent,
                    }
              }
            >
              {blank ? "blank editor" : "faded"}
            </span>
          </div>
          <p className="mt-1 text-[13px] leading-[1.65] text-ink/75">
            <InlineText text={exercise.task} />
          </p>
          {exercise.repo && (
            <div className="mt-1.5 font-mono text-[10.5px] text-graphite">
              <span className="rounded border border-line bg-ink/[0.03] px-1.5 py-0.5">
                repo: {exercise.repo}
              </span>
            </div>
          )}
          {blank && (
            <div className="mt-1.5 font-mono text-[10.5px] text-graphite">
              <span className="rounded border border-dashed border-line px-1.5 py-0.5">
                no repo — new directory, uv init, nothing else
              </span>
            </div>
          )}
          <button
            type="button"
            onClick={() => setShowSolution((v) => !v)}
            aria-expanded={showSolution}
            className="mt-2 inline-flex items-center gap-1 font-mono text-[11px] underline-offset-2 hover:underline"
            style={{ color: accent }}
          >
            <HugeiconsIcon
              icon={showSolution ? MinusSignIcon : PlusSignIcon}
              size={12}
              strokeWidth={2.5}
            />
            {blank
              ? showSolution
                ? "hide the bar"
                : "what a good answer proves"
              : showSolution
                ? "hide solution notes"
                : "solution notes"}
          </button>
        </div>
      </div>
      {showSolution && (
        <div className="ml-[35px] border-t border-line/60 px-4 pt-3 pb-4">
          <ul className="space-y-1.5">
            {exercise.solution.map((step, i) => (
              <li key={i} className="flex gap-2 text-[12.5px] leading-relaxed text-ink/80">
                <span className="shrink-0 font-mono" style={{ color: accent }}>
                  ›
                </span>
                <span>
                  <InlineText text={step} />
                </span>
              </li>
            ))}
          </ul>
          {exercise.code && (
            <CodeBlock code={exercise.code} title="reference implementation" accent={accent} />
          )}
        </div>
      )}
    </div>
  );
}
