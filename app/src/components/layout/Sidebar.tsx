import BookmarkAdd02Icon from "@hugeicons/core-free-icons/BookmarkAdd02Icon";
import Home01Icon from "@hugeicons/core-free-icons/Home01Icon";
import Moon02Icon from "@hugeicons/core-free-icons/Moon02Icon";
import Sun03Icon from "@hugeicons/core-free-icons/Sun03Icon";
import { HugeiconsIcon } from "@hugeicons/react";
import { phases } from "../../data/phases";
import type { Theme } from "../../lib/progress";
import { ProgressRing } from "../ui/ProgressRing";

interface SidebarProps {
  view: string;
  onNav: (view: string) => void;
  phasePct: (phaseId: string) => number;
  overallPct: number;
  theme: Theme;
  onTheme: () => void;
  onClose?: () => void;
}

export function Sidebar({
  view,
  onNav,
  phasePct,
  overallPct,
  theme,
  onTheme,
  onClose,
}: SidebarProps) {
  const navigate = (next: string) => {
    onNav(next);
    onClose?.();
  };

  return (
    <div className="flex h-full flex-col border-r border-line bg-card">
      <button
        type="button"
        onClick={() => navigate("dash")}
        className="border-b border-line/70 px-5 pt-6 pb-4 text-left hover:bg-ink/[0.02]"
      >
        <div className="font-mono text-[9.5px] uppercase tracking-[0.22em] text-graphite">
          Workbook · 2026
        </div>
        <div className="mt-1 text-[15px] font-bold leading-tight tracking-tight text-ink">
          GenAI Engineer
        </div>
        <div className="mt-2.5 flex items-center gap-2">
          <div className="h-[5px] flex-1 overflow-hidden rounded-full bg-ink/10">
            <div
              className="h-full rounded-full bg-ink transition-all duration-500"
              style={{ width: `${overallPct * 100}%` }}
            />
          </div>
          <span className="font-mono text-[10px] text-graphite">
            {Math.round(overallPct * 100)}%
          </span>
        </div>
      </button>

      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <button
          type="button"
          onClick={() => navigate("dash")}
          className={`mb-3 flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-[12.5px] font-semibold transition-colors ${
            view === "dash" ? "bg-ink text-paper" : "text-ink/80 hover:bg-ink/[0.05]"
          }`}
        >
          <HugeiconsIcon icon={Home01Icon} size={15} strokeWidth={2} />
          Dashboard &amp; prerequisites
        </button>

        <div className="relative ml-[21px]">
          <div className="absolute left-[-1px] top-3 bottom-3 w-[2px] bg-ink/10" />
          <div className="space-y-1">
            {phases.map((phase) => {
              const active = view === phase.id;
              const pct = phasePct(phase.id);
              return (
                <button
                  type="button"
                  key={phase.id}
                  onClick={() => navigate(phase.id)}
                  className={`relative w-full rounded-r-md py-2 pl-5 pr-2 text-left transition-colors ${
                    active ? "" : "hover:bg-ink/[0.04]"
                  }`}
                  style={
                    active
                      ? { background: `color-mix(in oklab, ${phase.color} 12%, transparent)` }
                      : undefined
                  }
                >
                  <span className="absolute left-[-7px] top-[13px]">
                    <ProgressRing pct={pct} color={phase.color} size={14} />
                  </span>
                  <span
                    className="absolute left-[-3.5px] top-[16.5px] h-[7px] w-[7px] rounded-full"
                    style={{ background: pct >= 1 || active ? phase.color : "transparent" }}
                  />
                  <div
                    className="font-mono text-[9.5px] uppercase tracking-[0.14em]"
                    style={{ color: phase.color }}
                  >
                    Phase {String(phase.num).padStart(2, "0")}
                  </div>
                  <div
                    className={`text-[12.5px] leading-snug ${
                      active ? "font-bold text-ink" : "font-medium text-ink/75"
                    }`}
                  >
                    {phase.title}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Outside the phase rail on purpose: no ring, no number, dashed border.
            Electives carry no progress, and the chrome should say so before the
            student clicks. */}
        <button
          type="button"
          onClick={() => navigate("electives")}
          className={`mt-4 flex w-full items-center gap-2 rounded-md border border-dashed px-3 py-2 text-left transition-colors ${
            view === "electives" ? "border-ink/40 bg-ink/[0.06]" : "border-line hover:bg-ink/[0.04]"
          }`}
        >
          <HugeiconsIcon
            icon={BookmarkAdd02Icon}
            size={15}
            strokeWidth={2}
            className="text-graphite"
          />
          <span>
            <span className="block text-[12.5px] font-semibold leading-snug text-ink/80">
              Electives shelf
            </span>
            <span className="block font-mono text-[9px] uppercase tracking-[0.14em] text-graphite">
              Optional · unscored
            </span>
          </span>
        </button>
      </nav>

      <div className="flex items-center justify-between gap-2 border-t border-line/70 px-5 py-4">
        <p className="font-mono text-[9.5px] leading-relaxed tracking-wide text-graphite">
          GATES, NOT DATES.
          <br />
          SHIP WITH METRICS.
        </p>
        <button
          type="button"
          onClick={onTheme}
          aria-label="Toggle light/dark theme"
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-line bg-ink/[0.03] text-ink transition-colors hover:bg-ink/[0.07]"
        >
          <HugeiconsIcon icon={theme === "dark" ? Sun03Icon : Moon02Icon} size={17} />
        </button>
      </div>
    </div>
  );
}
