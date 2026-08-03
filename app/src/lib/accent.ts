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

/**
 * The accent, darkened enough to carry white text.
 *
 * An accent has one job in this palette: be legible *as text* on paper and on a
 * card. `accentContrastFindings` checks exactly that and every accent passes it in
 * both themes. Filling a block with the accent and writing white on top is the
 * inverse job, and the dark accents fail it badly — white on `#1AAD7B` is 2.48:1
 * against a 4.5:1 requirement, and the same held for all nine.
 *
 * The light accents are already dark enough, and only just: 4.81 to 4.90:1 across
 * the nine, which is a palette that was tuned for this and a reason not to touch
 * it. So the scrim is 0% in light and 40% in dark, set in `index.css` beside the
 * rest of the theme.
 *
 * The three places that need this are the workshop header, the ladder chip on an
 * exercise card, and a selected answer button. They went unnoticed because axe can
 * only decide contrast for an element it can sample, and all three sat thousands
 * of pixels below the viewport on an unfolded phase page.
 */
export function accentUnderWhite(accent: string): string {
  return `color-mix(in oklab, #000 var(--accent-scrim, 0%), ${accent})`;
}
