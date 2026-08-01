import type { Phase } from "../data/types";

/** Kept identical to the shipped bundle so existing student progress loads. */
const PROGRESS_KEY = "genai_workbook_progress_v1";
const THEME_KEY = "genai_workbook_theme";

export type Progress = Record<string, boolean>;
export type Theme = "light" | "dark";

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
