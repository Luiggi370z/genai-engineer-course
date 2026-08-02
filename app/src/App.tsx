import Menu01Icon from "@hugeicons/core-free-icons/Menu01Icon";
import Moon02Icon from "@hugeicons/core-free-icons/Moon02Icon";
import Sun03Icon from "@hugeicons/core-free-icons/Sun03Icon";
import { HugeiconsIcon } from "@hugeicons/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Dashboard } from "./components/layout/Dashboard";
import { ElectivesView } from "./components/layout/ElectivesView";
import { Sidebar } from "./components/layout/Sidebar";
import { PhaseView } from "./components/phase/PhaseView";
import { prerequisites } from "./data/intro";
import { phases } from "./data/phases";
import {
  clearProgress,
  exportProgressFile,
  loadProgress,
  loadTheme,
  type Progress,
  parseProgressFile,
  phaseIds,
  saveProgress,
  saveTheme,
  type Theme,
} from "./lib/progress";

export function App() {
  const [progress, setProgress] = useState<Progress | null>(null);
  const [theme, setTheme] = useState<Theme>("light");
  const [view, setView] = useState<string>("dash");
  const [navOpen, setNavOpen] = useState(false);
  const navDialogRef = useRef<HTMLElement>(null);
  const menuButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    setProgress(loadProgress());
    setTheme(loadTheme());
  }, []);

  // Dialog semantics for the mobile nav: focus moves in on open, Escape closes,
  // Tab cycles inside, and focus lands back on the menu button on close.
  useEffect(() => {
    if (!navOpen) return;
    const dialog = navDialogRef.current;
    dialog?.focus();

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setNavOpen(false);
        return;
      }
      if (event.key !== "Tab" || !dialog) return;
      const focusables = Array.from(
        dialog.querySelectorAll<HTMLElement>(
          "button, a[href], input, [tabindex]:not([tabindex='-1'])",
        ),
      );
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      if (!first || !last) return;
      const current = document.activeElement;
      if (event.shiftKey && (current === first || current === dialog)) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && current === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      menuButtonRef.current?.focus();
    };
  }, [navOpen]);

  const toggle = useCallback((id: string) => {
    setProgress((current) => {
      const next: Progress = { ...current, [id]: !current?.[id] };
      saveProgress(next);
      return next;
    });
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme((current) => {
      const next: Theme = current === "dark" ? "light" : "dark";
      saveTheme(next);
      return next;
    });
  }, []);

  const navigate = useCallback((next: string) => {
    setView(next);
    document.getElementById("main-scroll")?.scrollTo({ top: 0 });
  }, []);

  const exportProgress = useCallback(() => {
    const blob = new Blob([exportProgressFile(loadProgress())], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "genai-workbook-progress.json";
    link.click();
    URL.revokeObjectURL(url);
  }, []);

  const importProgress = useCallback((file: File) => {
    void file.text().then((raw) => {
      const next = parseProgressFile(raw);
      if (next === null) {
        window.alert("That file doesn't look like a workbook progress export.");
        return;
      }
      saveProgress(next);
      setProgress(next);
    });
  }, []);

  const resetProgress = useCallback(() => {
    if (!window.confirm("Reset all progress? Export a backup first if in doubt.")) return;
    clearProgress();
    setProgress({});
  }, []);

  const phasePct = useMemo(
    () => (phaseId: string) => {
      if (!progress) return 0;
      const phase = phases.find((p) => p.id === phaseId);
      if (!phase) return 0;
      const ids = phaseIds(phase);
      return ids.length ? ids.filter((id) => progress[id]).length / ids.length : 0;
    },
    [progress],
  );

  // Prerequisites plus the nine phases, and deliberately nothing else. The electives
  // shelf has no checkable ids, so skipping every optional side quest still reaches
  // 100% — otherwise "optional" would quietly render as "incomplete".
  const overallPct = useMemo(() => {
    if (!progress) return 0;
    const ids = [...prerequisites.map((p) => p.id), ...phases.flatMap(phaseIds)];
    return ids.filter((id) => progress[id]).length / ids.length;
  }, [progress]);

  if (!progress) {
    return (
      <div className="light grid-bg flex h-screen items-center justify-center">
        <div className="animate-pulse font-mono text-[12px] tracking-[0.2em] text-graphite">
          LOADING YOUR PROGRESS…
        </div>
      </div>
    );
  }

  const activePhase = phases.find((p) => p.id === view);
  const nextPhase = activePhase ? phases.find((p) => p.num === activePhase.num + 1) : undefined;

  return (
    <div className={theme === "dark" ? "dark" : "light"}>
      <div className="grid-bg flex h-screen overflow-hidden text-ink">
        {/* Plain anchor on purpose: `main` carries tabIndex={-1}, so the default
            fragment navigation moves focus into the content, no JS needed. */}
        <a href="#main-scroll" className="skip-link">
          Skip to content
        </a>
        <aside className="hidden w-[248px] shrink-0 md:block">
          <Sidebar
            view={view}
            onNav={navigate}
            phasePct={phasePct}
            overallPct={overallPct}
            theme={theme}
            onTheme={toggleTheme}
            onExport={exportProgress}
            onImport={importProgress}
            onReset={resetProgress}
          />
        </aside>

        {navOpen && (
          <div className="fixed inset-0 z-40 md:hidden">
            <button
              type="button"
              aria-label="Close navigation"
              className="absolute inset-0 bg-black/35"
              onClick={() => setNavOpen(false)}
            />
            <aside
              ref={navDialogRef}
              role="dialog"
              aria-modal="true"
              aria-label="Course navigation"
              tabIndex={-1}
              className="absolute bottom-0 left-0 top-0 w-[262px] shadow-2xl outline-none"
            >
              <Sidebar
                view={view}
                onNav={navigate}
                phasePct={phasePct}
                overallPct={overallPct}
                theme={theme}
                onTheme={toggleTheme}
                onClose={() => setNavOpen(false)}
                onExport={exportProgress}
                onImport={importProgress}
                onReset={resetProgress}
              />
            </aside>
          </div>
        )}

        <div className="flex min-w-0 flex-1 flex-col">
          {/* A `header` rather than a `div`: the phase title in here is the only
              content on a phone that would otherwise sit outside every landmark,
              which leaves a screen reader jumping by region unable to reach it. */}
          <header className="flex items-center gap-3 border-b border-line bg-card px-4 py-3 md:hidden">
            <button
              ref={menuButtonRef}
              type="button"
              onClick={() => setNavOpen(true)}
              aria-label="Open navigation"
              aria-haspopup="dialog"
              aria-expanded={navOpen}
              className="p-1 text-ink"
            >
              <HugeiconsIcon icon={Menu01Icon} size={18} strokeWidth={2} />
            </button>
            <span className="truncate font-mono text-[11px] uppercase tracking-[0.18em] text-graphite">
              {activePhase
                ? `Phase ${String(activePhase.num).padStart(2, "0")} · ${activePhase.title}`
                : view === "electives"
                  ? "Electives shelf · optional"
                  : "GenAI Engineer Workbook"}
            </span>
            <button
              type="button"
              onClick={toggleTheme}
              aria-label="Toggle theme"
              className="ml-auto rounded border border-line px-2 py-1 text-ink"
            >
              <HugeiconsIcon icon={theme === "dark" ? Sun03Icon : Moon02Icon} size={16} />
            </button>
          </header>

          <main
            id="main-scroll"
            tabIndex={-1}
            className="flex-1 overflow-y-auto px-5 py-8 outline-none sm:px-8 lg:px-12"
          >
            {activePhase ? (
              <PhaseView
                phase={activePhase}
                progress={progress}
                onToggle={toggle}
                onNav={navigate}
                nextPhase={nextPhase}
              />
            ) : view === "electives" ? (
              <ElectivesView onNav={navigate} />
            ) : (
              <Dashboard
                progress={progress}
                onToggle={toggle}
                onNav={navigate}
                phasePct={phasePct}
                overallPct={overallPct}
              />
            )}
          </main>
        </div>
      </div>
    </div>
  );
}
