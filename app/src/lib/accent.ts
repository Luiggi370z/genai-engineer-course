import type { CSSProperties } from "react";
import { phases } from "../data/phases";
import type { Theme } from "./progress";

/**
 * Phase accents reach the DOM as custom properties, not as literal hex.
 *
 * Every accent now has a light and a dark value, and the components that use
 * one (the sidebar rail, the dashboard cards, and everything under a phase
 * view) are spread across the tree — threading `theme` into all of them would
 * put a prop on components that have no other reason to know what theme is.
 * Instead the app root publishes `--accent-<phase id>` for the current theme
 * and each component asks for `var(--accent-p3)`. The cascade does the work,
 * `color-mix()` accepts a var like any other colour, and there is exactly one
 * place where a theme becomes a palette.
 */
export function accentVars(theme: Theme): CSSProperties {
  return Object.fromEntries(
    phases.map((phase) => [`--accent-${phase.id}`, phase.accent[theme]]),
  ) as CSSProperties;
}

/** The accent of one phase, as a CSS value usable anywhere a colour is. */
export function accentOf(phaseId: string): string {
  return `var(--accent-${phaseId})`;
}
