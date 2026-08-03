import type { Phase } from "../data/types";

/**
 * Roughly how tall a phase section renders on a phone, from the content data.
 *
 * This exists to answer one question — is this section long enough that a phone
 * reader should be offered it collapsed — and it answers it from the data rather
 * than from layout. Measuring the real height would be more direct and is the
 * wrong trade: it means rendering the section expanded, measuring it, then
 * collapsing it, which the reader sees as a flash on every page load.
 *
 * The estimate is a proxy and only has to be good enough to sort sections into
 * "longer than two screens" and "not", which the measurements make an easy call
 * rather than a close one. Taken from the shipped build at 390x844, per row:
 *
 *   concept block        290-436px   (44 blocks -> 12,755px on phase 1)
 *   exercise card        453-577px
 *   workshop deliverable 292-496px
 *   question-bank item   85px
 *
 * The four sections below all clear the threshold on every phase by at least
 * 20%, and the five sections not listed here measured under 1,200px on every
 * phase. Nothing sits near the line, so a drifting constant changes no verdict.
 */
const ROW_PX = {
  conceptBlock: 320,
  exercise: 510,
  deliverable: 430,
  question: 85,
} as const;

/** A phone screen, from the viewport the accessibility sweep already scans. */
const PHONE_VIEWPORT_PX = 844;

/**
 * How many screens a section may fill before collapsing is offered.
 *
 * Two, because one screen is not a scrolling problem and three means whatever
 * follows the section is unreachable without a deliberate hunt. The audit asked
 * for this on "exceptionally long" pages and the measurements agree with the
 * adjective: phase 8 runs 26,295px on a phone, which is 31 screens, and two
 * sections are more than half of it.
 */
const SCREENS_BEFORE_COLLAPSING = 2;

/** Estimated height above which a narrow viewport offers a section collapsed. */
export const LONG_SECTION_PX = PHONE_VIEWPORT_PX * SCREENS_BEFORE_COLLAPSING;

/**
 * Estimated rendered height of a phase section, in px.
 *
 * Deliberately not one formula. A concept card's height comes from its blocks, an
 * exercise's from the card, a workshop's from its deliverables — and a section
 * this does not know about returns 0, which reads as "never long enough to
 * collapse". That default is the safe direction: it leaves the section open.
 */
export function sectionHeight(phase: Phase, id: string): number {
  switch (id) {
    case "concepts":
      return (
        phase.concepts.reduce((rows, concept) => rows + concept.blocks.length, 0) *
        ROW_PX.conceptBlock
      );
    case "exercises":
      return phase.exercises.length * ROW_PX.exercise;
    case "workshop":
      return (phase.workshop?.deliverables.length ?? 0) * ROW_PX.deliverable;
    case "qbank":
      return (
        (phase.qbank ?? []).reduce((rows, group) => rows + group.items.length, 0) * ROW_PX.question
      );
    default:
      return 0;
  }
}

/** Whether a narrow viewport should offer this section collapsed. */
export function isLongSection(phase: Phase, id: string): boolean {
  return sectionHeight(phase, id) > LONG_SECTION_PX;
}
