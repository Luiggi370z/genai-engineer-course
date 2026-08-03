import type { Effort } from "../data/types";

/** The marker the lesson README uses, so the gate and the app agree on one line. */
export const EFFORT_PREFIX = "**Effort.**";

/**
 * The one rendering of an effort estimate.
 *
 * Written once and used twice: the workbook prints it on the exercise card, and
 * the integrity gate re-renders it from the same data and demands the lesson
 * README say exactly this. That is the whole mechanism — the number a learner
 * reads in the app cannot drift from the number the lesson claims, because
 * neither is typed twice.
 *
 * Three numbers rather than one because "~40 min" was answering three different
 * questions at once. The fast tier is offline and is what most people mean by
 * finishing a lesson. The integration tier downloads weights and starts
 * containers, and is time you spend whether or not your code is right.
 * Realistic is the honest total for a first pass: reading the README, being
 * wrong twice, and looking something up.
 */
export function formatEffort(effort: Effort): string {
  return render(effort, `~${duration(effort.fast)} to green on the fast tests`);
}

/**
 * The same three tiers for a workshop, said in workshop language.
 *
 * A workshop has no "fast tests" to go green — it is hours of building against
 * a brief. Sharing the tiers but not the wording is the point of the audit's
 * finding: a learner planning a weekend needs to see that a workshop is a
 * different order of magnitude from a lesson, not the same sentence with
 * bigger numbers.
 */
export function formatWorkshopEffort(effort: Effort): string {
  return render(effort, `~${duration(effort.fast)} of focused build time`);
}

function render(effort: Effort, fast: string): string {
  const integration =
    effort.integration === null
      ? "no integration tier"
      : `+${duration(effort.integration)} for the integration tier`;
  return `${fast} · ${integration} · ~${duration(effort.realistic)} realistic first pass`;
}

/** The short form for a card, where the sentence does not fit. */
export function summarizeEffort(effort: Effort): string {
  const tiers = [`~${duration(effort.fast)}`];
  if (effort.integration !== null) tiers.push(`+${duration(effort.integration)} integration`);
  tiers.push(`~${duration(effort.realistic)} first pass`);
  return tiers.join(" · ");
}

/**
 * Minutes up to two hours, hours past that.
 *
 * "~480 min" is a number you have to convert before you can decide whether you
 * have time today, and the conversion is the whole reason the estimate exists.
 * Every estimate in the course is a multiple of 30, so the hour form is exact
 * rather than rounded.
 */
function duration(min: number): string {
  if (min < 120) return `${min} min`;
  const hours = min / 60;
  return `${Number.isInteger(hours) ? hours : hours.toFixed(1)} h`;
}
