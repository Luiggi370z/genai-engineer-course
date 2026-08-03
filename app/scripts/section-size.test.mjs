import assert from "node:assert/strict";
import test from "node:test";
import { loadCourseData } from "./lib/load-data.mjs";

/**
 * The mobile collapse decides which sections a phone folds, and it decides it from
 * an estimate. An estimate is only worth trusting if something checks it against
 * the thing it estimates, so these tests carry the measurements.
 *
 * Taken from the shipped build in headless Chromium at 390x844, per section, as
 * the distance from one section anchor to the next.
 */
// biome-ignore format: one row per phase is the point — this is a measurement table.
const MEASURED_PX = {
  1: { objectives: 627, concepts: 12755, example: 308, exercises: 2851, workshop: 3158, checkpoint: 1183, resources: 713 },
  2: { objectives: 431, recall: 643, concepts: 8506, example: 308, exercises: 2586, workshop: 2978, checkpoint: 798, resources: 426 },
  3: { objectives: 540, recall: 550, concepts: 9396, example: 422, exercises: 2623, workshop: 2977, checkpoint: 972, resources: 497 },
  4: { objectives: 540, recall: 513, concepts: 7184, example: 330, exercises: 2592, workshop: 2553, checkpoint: 953, resources: 425 },
  5: { objectives: 540, recall: 531, concepts: 9065, example: 514, exercises: 2572, workshop: 2827, checkpoint: 1009, resources: 605 },
  6: { objectives: 453, recall: 550, concepts: 7842, example: 399, exercises: 2162, workshop: 2941, checkpoint: 816, resources: 446 },
  7: { objectives: 453, recall: 494, concepts: 6552, example: 353, exercises: 2011, workshop: 2422, checkpoint: 835, resources: 425 },
  8: { objectives: 518, recall: 531, concepts: 12799, example: 330, exercises: 2887, workshop: 6718, checkpoint: 1109, resources: 635 },
  9: { objectives: 409, recall: 513, concepts: 3579, example: 335, exercises: 1811, workshop: 3344, checkpoint: 660, qbank: 1694, resources: 367 },
};

/** The four sections the estimator knows how to size. */
const SIZED = ["concepts", "exercises", "workshop", "qbank"];

const { phases } = await loadCourseData();
const { isLongSection, sectionHeight, LONG_SECTION_PX } = await import(
  "../src/lib/section-size.ts"
);

test("every section the estimator sizes really is over two screens", () => {
  // The direction that matters: nothing gets folded that a phone could have
  // scrolled past comfortably.
  for (const phase of phases) {
    for (const id of SIZED) {
      if (!isLongSection(phase, id)) continue;
      const measured = MEASURED_PX[phase.num][id];
      assert.ok(
        measured > LONG_SECTION_PX,
        `phase ${phase.num} ${id}: folded, but measures ${measured}px, under the ${LONG_SECTION_PX}px bar`,
      );
    }
  }
});

test("every section over two screens really does get folded", () => {
  // The other direction: no 12,000px section quietly escapes because the
  // estimator undercounted it.
  for (const phase of phases) {
    for (const [id, measured] of Object.entries(MEASURED_PX[phase.num])) {
      if (measured <= LONG_SECTION_PX) continue;
      assert.ok(
        isLongSection(phase, id),
        `phase ${phase.num} ${id} measures ${measured}px and is not folded`,
      );
    }
  }
});

test("the estimate stays within 2x of the measurement", () => {
  // Loose on purpose — it is a proxy, not a layout engine. What it rules out is
  // the estimate drifting far enough that a verdict could flip.
  for (const phase of phases) {
    for (const id of SIZED) {
      const measured = MEASURED_PX[phase.num][id];
      if (measured === undefined) continue;
      const estimate = sectionHeight(phase, id);
      const ratio = estimate / measured;
      assert.ok(
        ratio > 0.5 && ratio < 2,
        `phase ${phase.num} ${id}: estimated ${estimate}px against ${measured}px measured (${ratio.toFixed(2)}x)`,
      );
    }
  }
});

test("the short sections are never folded, whatever the phase", () => {
  for (const phase of phases) {
    for (const id of ["objectives", "recall", "example", "checkpoint", "resources"]) {
      assert.equal(sectionHeight(phase, id), 0, `${id} should not be sized`);
      assert.equal(isLongSection(phase, id), false);
    }
  }
});

test("a phase with no workshop or question bank sizes them at zero", () => {
  const bare = { concepts: [], exercises: [], num: 0 };
  assert.equal(sectionHeight(bare, "workshop"), 0);
  assert.equal(sectionHeight(bare, "qbank"), 0);
  assert.equal(isLongSection(bare, "workshop"), false);
});

test("an unknown section id is not long, rather than throwing", () => {
  assert.equal(sectionHeight(phases[0], "not-a-section"), 0);
  assert.equal(isLongSection(phases[0], "not-a-section"), false);
});

test("folding is what the audit asked for: most of a phase, on a phone", () => {
  // Not a boundary check — a statement of the effect size, so a future change
  // that quietly stops folding anything fails here rather than in an audit.
  for (const phase of phases) {
    const measured = MEASURED_PX[phase.num];
    const total = Object.values(measured).reduce((n, px) => n + px, 0);
    const folded = SIZED.filter((id) => isLongSection(phase, id)).reduce(
      (n, id) => n + (measured[id] ?? 0),
      0,
    );
    const share = folded / total;
    assert.ok(
      share > 0.6,
      `phase ${phase.num}: folding only removes ${Math.round(share * 100)}% of the page`,
    );
  }
});
