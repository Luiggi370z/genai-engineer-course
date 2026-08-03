import type { Phase } from "../data/types";

/** Kept identical to the shipped bundle so existing student progress loads. */
const PROGRESS_KEY = "genai_workbook_progress_v1";
const THEME_KEY = "genai_workbook_theme";
const PLACE_KEY = "genai_workbook_place_v1";

export type Progress = Record<string, boolean>;
export type Theme = "light" | "dark";

/**
 * Where the reader was: which view, and how far down it.
 *
 * Its own key rather than a field on progress, because the two have different
 * lifetimes — `Reset progress` clears what you have done and must not also
 * forget where you were reading, and an exported progress file is a record of
 * work, not of a scroll position on somebody else's laptop.
 */
export interface Place {
  view: string;
  sectionId?: string;
}

/**
 * Every checkable id in a phase, in the order a student meets them. This is the
 * denominator of the phase progress ring, so anything checkable must be here.
 */
export function phaseIds(phase: Phase): string[] {
  return [
    ...phase.objectives.map((o) => o.id),
    ...(phase.recall?.map((r) => r.id) ?? []),
    ...phase.exercises.map((e) => e.id),
    ...(phase.workshop?.deliverables.map((d) => d.id) ?? []),
    ...(phase.checkpoint?.map((q) => q.id) ?? []),
    ...(phase.qbank?.flatMap((g) => g.items.map((q) => q.id)) ?? []),
  ];
}

export function loadProgress(): Progress {
  try {
    const raw = localStorage.getItem(PROGRESS_KEY);
    if (!raw) return {};
    const parsed: unknown = JSON.parse(raw);
    if (typeof parsed !== "object" || parsed === null) return {};
    return parsed as Progress;
  } catch {
    return {};
  }
}

export function saveProgress(progress: Progress): void {
  try {
    localStorage.setItem(PROGRESS_KEY, JSON.stringify(progress));
  } catch {
    // Private-browsing or a full quota: progress is a convenience, never a blocker.
  }
}

export function loadTheme(): Theme {
  try {
    const stored = localStorage.getItem(THEME_KEY);
    if (stored === "light" || stored === "dark") return stored;
  } catch {
    // fall through to the OS preference
  }
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function saveTheme(theme: Theme): void {
  try {
    localStorage.setItem(THEME_KEY, theme);
  } catch {
    // see saveProgress
  }
}

export function loadPlace(): Place | null {
  try {
    const raw = localStorage.getItem(PLACE_KEY);
    if (!raw) return null;
    const parsed: unknown = JSON.parse(raw);
    if (typeof parsed !== "object" || parsed === null) return null;
    const box = parsed as Record<string, unknown>;
    if (typeof box.view !== "string" || !box.view) return null;
    return typeof box.sectionId === "string"
      ? { view: box.view, sectionId: box.sectionId }
      : { view: box.view };
  } catch {
    return null;
  }
}

export function savePlace(place: Place): void {
  try {
    localStorage.setItem(PLACE_KEY, JSON.stringify(place));
  } catch {
    // see saveProgress
  }
}

/**
 * A percentage that does not round a start into nothing.
 *
 * `Math.round(1/252 * 100)` is `0`, so a reader who ticked their first box was
 * told they had made no progress — the one moment in the course where the
 * number is doing motivational work. The two guard bands say "you have started"
 * and "you are not finished" without inventing precision: everything between
 * those reads as an ordinary rounded percentage.
 */
export function formatPct(pct: number): string {
  if (pct >= 1) return "100%";
  if (pct > 0.99) return ">99%";
  if (pct <= 0) return "0%";
  if (pct < 0.01) return "<1%";
  return `${Math.round(pct * 100)}%`;
}

/** Done and total for a set of checkable ids — the number behind the ring. */
export function tally(progress: Progress, ids: string[]): { done: number; total: number } {
  return { done: ids.filter((id) => progress[id]).length, total: ids.length };
}

/**
 * Serialize progress for download. Versioned and timestamped so a future format
 * change can migrate old files instead of rejecting them.
 */
export function exportProgressFile(progress: Progress): string {
  return JSON.stringify({ version: 1, exportedAt: new Date().toISOString(), progress }, null, 2);
}

/**
 * Parse an uploaded progress file. Accepts the versioned export shape or a bare
 * `{id: boolean}` map, drops anything that isn't a boolean entry, and returns
 * null (never throws) on garbage — the caller decides how to tell the user.
 */
export function parseProgressFile(raw: string): Progress | null {
  try {
    const parsed: unknown = JSON.parse(raw);
    if (typeof parsed !== "object" || parsed === null) return null;
    const box = parsed as Record<string, unknown>;
    const map = "progress" in box ? box.progress : parsed;
    if (typeof map !== "object" || map === null) return null;
    const entries = Object.entries(map as Record<string, unknown>).filter(
      ([, value]) => typeof value === "boolean",
    );
    return Object.fromEntries(entries) as Progress;
  } catch {
    return null;
  }
}

export function clearProgress(): void {
  try {
    localStorage.removeItem(PROGRESS_KEY);
  } catch {
    // see saveProgress
  }
}
