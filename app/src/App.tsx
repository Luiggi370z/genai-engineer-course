import Menu01Icon from "@hugeicons/core-free-icons/Menu01Icon";
import Moon02Icon from "@hugeicons/core-free-icons/Moon02Icon";
import Sun03Icon from "@hugeicons/core-free-icons/Sun03Icon";
import { HugeiconsIcon } from "@hugeicons/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Dashboard } from "./components/layout/Dashboard";
import { ElectivesView } from "./components/layout/ElectivesView";
import { Sidebar } from "./components/layout/Sidebar";
import { PhaseView } from "./components/phase/PhaseView";
import { goToSection } from "./components/phase/useActiveSection";
import { prerequisites } from "./data/intro";
import { phases } from "./data/phases";
import { accentVars } from "./lib/accent";
import {
  clearProgress,
  exportProgressFile,
  loadPlace,
  loadProgress,
  loadTheme,
  type Place,
  type Progress,
  parseProgressFile,
  phaseIds,
  savePlace,
  saveProgress,
  saveTheme,
  type Theme,
  tally,
} from "./lib/progress";

export function App() {
  const [progress, setProgress] = useState<Progress | null>(null);
  const [theme, setTheme] = useState<Theme>("light");
  const [view, setView] = useState<string>("dash");
  // Where the reader was last time, offered rather than restored: the app opens
  // on the dashboard, and a Resume card takes them back. Jumping straight into
  // the middle of Phase 5 on a cold open would be a surprise, and the dashboard
  // is also where the prerequisites and the manifest live.
  const [place, setPlace] = useState<Place | null>(null);
  const [navOpen, setNavOpen] = useState(false);
  const navDialogRef = useRef<HTMLDivElement>(null);
  const menuButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    setProgress(loadProgress());
    setTheme(loadTheme());
    setPlace(loadPlace());
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
    // Only phases are places you resume to. The dashboard is where Resume is
    // offered, and the electives shelf is a shelf — going to either leaves the
    // last phase on offer. The section is dropped rather than carried over: you
    // are at the top of a different page now, and keeping "Workshop" from the
    // phase you just left would send the next Resume click somewhere you have
    // never been.
    if (!phases.some((phase) => phase.id === next)) return;
    const here = { view: next };
    savePlace(here);
    setPlace(here);
  }, []);

  // Reported by `PhaseView` as the reader scrolls. Written straight through to
  // storage rather than held in state and flushed on unload: a browser tab that
  // is closed, crashed or discarded never runs an unload handler, and losing a
  // reading position to a crash is exactly the case this feature is for.
  const rememberSection = useCallback((sectionId: string) => {
    setPlace((current) => {
      if (!current || current.sectionId === sectionId) return current;
      const next = { view: current.view, sectionId };
      savePlace(next);
      return next;
    });
  }, []);

  const resume = useCallback(() => {
    if (!place) return;
    const target = place.sectionId;
    setView(place.view);
    if (!target) {
      document.getElementById("main-scroll")?.scrollTo({ top: 0 });
      return;
    }
    // Two frames, not one: the phase has to mount before its sections exist,
    // and `scrollIntoView` on an element that is not there yet is a no-op that
    // silently leaves the reader at the top.
    requestAnimationFrame(() => requestAnimationFrame(() => goToSection(target)));
  }, [place]);

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
  //
  // The count travels with the percentage. A ring at "<1%" is honest and still
  // opaque; "1 of 252" says what the denominator is and how big the course
  // actually is, which is the question the percentage was standing in for.
  const overall = useMemo(
    () => tally(progress ?? {}, [...prerequisites.map((p) => p.id), ...phases.flatMap(phaseIds)]),
    [progress],
  );
  const overallPct = overall.total ? overall.done / overall.total : 0;

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
    <div className={theme === "dark" ? "dark" : "light"} style={accentVars(theme)}>
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
            {/* A `div`, not an `aside`: `role="dialog"` on a complementary
                landmark is a role conflict, and the element is a dialog here,
                not a sidebar. */}
            <div
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
            </div>
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
                onSection={rememberSection}
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
                overall={overall}
                place={place}
                onResume={resume}
              />
            )}
          </main>
        </div>
      </div>
    </div>
  );
}
