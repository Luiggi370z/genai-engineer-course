/**
 * The alignment rules, as a pure function over course data.
 *
 * Purely pedagogical: does the phase teach what it tests, in an order a student
 * could actually follow. Id uniqueness and repo-path existence used to live here
 * too, but they are questions about whether the data is well-formed rather than
 * about whether it teaches — they now sit in `integrity.mjs` with the rest of
 * that concern.
 *
 * Kept separate from the CLI so `alignment.test.mjs` can feed it synthetic
 * phases and prove every rule actually fires. A gate nobody has seen fail is
 * not a gate.
 */

/**
 * Bloom's revised taxonomy. The level is what makes an objective checkable
 * against its assessment: you can prove "Implement" with a repo, but demanding
 * a repo for "Explain" is theatre — a checkpoint question is the fit there.
 */
export const BLOOM = {
  remember: ["define", "list", "name", "recall", "identify"],
  understand: ["explain", "describe", "summarize", "contrast", "classify", "interpret"],
  apply: ["implement", "build", "run", "use", "consume", "containerize", "deploy", "rehearse"],
  analyze: ["diagnose", "compare", "analyze", "differentiate", "audit", "measure", "estimate"],
  evaluate: ["justify", "critique", "defend", "judge", "calibrate", "choose", "evaluate", "gate"],
  create: [
    "design",
    "construct",
    "engineer",
    "orchestrate",
    "compose",
    "instrument",
    "optimize",
    "rewrite",
    "contain",
    "combine",
    "constrain",
  ],
};

export const LEVEL_OF = new Map();
for (const [level, verbs] of Object.entries(BLOOM)) {
  for (const verb of verbs) LEVEL_OF.set(verb, level);
}

/** Above `understand`, an objective must be assessed by something the student builds. */
export const NEEDS_ARTIFACT = new Set(["apply", "analyze", "evaluate", "create"]);

export const leadVerb = (text) =>
  /^\*\*([A-Za-z]+)\*\*/.exec(text ?? "")?.[1]?.toLowerCase() ?? null;

/**
 * @param {object} input
 * @param {any[]} input.phases        course data, in order
 * @returns {{ errors: {rule: string, subject: string, message: string}[], counts: object }}
 */
export function audit({ phases }) {
  const errors = [];
  const fail = (rule, subject, message) => errors.push({ rule, subject, message });

  const phaseOf = new Map();
  for (const phase of phases) {
    for (const o of phase.objectives) phaseOf.set(o.id, phase);
  }
  const levelOf = (id) => {
    const text = phaseOf.get(id)?.objectives.find((o) => o.id === id)?.text;
    return LEVEL_OF.get(leadVerb(text) ?? "") ?? "apply";
  };

  for (const phase of phases) {
    const label = `phase ${phase.num} (${phase.id})`;
    const own = new Set(phase.objectives.map((o) => o.id));
    const taught = new Set();
    const assessed = new Set();

    for (const o of phase.objectives) {
      const verb = leadVerb(o.text);
      if (!verb) {
        fail("bloom-verb", o.id, `must open with a bolded verb: "${(o.text ?? "").slice(0, 60)}…"`);
      } else if (!LEVEL_OF.has(verb)) {
        fail(
          "bloom-verb",
          o.id,
          `"${verb}" is not in the Bloom vocabulary — add it or pick another verb`,
        );
      }
    }

    if (
      phase.objectives.length &&
      !phase.objectives.some((o) => NEEDS_ARTIFACT.has(levelOf(o.id)))
    ) {
      fail(
        "phase-depth",
        phase.id,
        `${label} has no objective above "understand" — it is a reading, not a phase`,
      );
    }

    for (const concept of phase.concepts) {
      if (!concept.teaches?.length) {
        fail(
          "concept-teaches",
          concept.id,
          "card teaches nothing — cut it or point it at an objective",
        );
      }
      for (const ref of concept.teaches ?? []) {
        if (!own.has(ref)) {
          fail(
            "teaches-resolves",
            concept.id,
            `teaches "${ref}", which is not an objective of ${label}`,
          );
        }
        taught.add(ref);
      }
    }

    const tasks = [
      ...phase.exercises.map((e) => ({ item: e, what: "exercise" })),
      ...(phase.workshop ? [{ item: phase.workshop, what: "workshop" }] : []),
    ];
    for (const { item, what } of tasks) {
      if (!item.assesses?.length) {
        fail(
          "assesses-present",
          item.id,
          `${what} assesses nothing — every task must test an objective`,
        );
      }
      for (const ref of item.assesses ?? []) {
        if (!own.has(ref)) {
          fail(
            "assesses-resolves",
            item.id,
            `assesses "${ref}", which is not an objective of ${label}`,
          );
          continue;
        }
        // The rule this whole script exists for.
        if (!taught.has(ref)) {
          fail(
            "taught-before-tested",
            item.id,
            `${what} assesses "${ref}" but no concept card in ${label} teaches it`,
          );
        }
        assessed.add(ref);
      }
      // A prerequisite must already have been taught, which means an earlier phase.
      for (const ref of item.needs ?? []) {
        const source = phaseOf.get(ref);
        if (!source) {
          fail("needs-resolves", item.id, `needs "${ref}", which is not an objective anywhere`);
        } else if (source.num >= phase.num) {
          fail(
            "needs-is-earlier",
            item.id,
            `needs "${ref}" from phase ${source.num}, which is not before phase ${phase.num}`,
          );
        }
      }
    }

    // The ladder's top rung. A phase whose hardest task still ships a scaffold has
    // taught the student to fill in blanks, which is the documented failure mode of
    // every copy-along course: recognition that reads like competence.
    const blanks = phase.exercises.filter((e) => e.rung === "independent");
    if (!blanks.length) {
      fail(
        "independent-per-phase",
        phase.id,
        `${label} has no blank-editor task — every phase needs one exercise at the independent rung`,
      );
    }
    for (const e of blanks) {
      if (e.code) {
        fail(
          "independent-has-no-code",
          e.id,
          "an independent task cannot ship a reference implementation — that is the scaffold it exists to remove",
        );
      }
      if (e.repo) {
        fail(
          "independent-has-no-code",
          e.id,
          `an independent task cannot point at a repo (${e.repo}) — a blank editor means an empty directory`,
        );
      }
    }

    // Retrieval practice, and it only counts as *interleaved* if the sources mix.
    const recall = phase.recall ?? [];
    const first = phase.num === 1;
    if (!first && recall.length < 3) {
      fail(
        "recall-count",
        phase.id,
        `${label} carries ${recall.length} recall check(s); every phase after the first needs at least 3`,
      );
    }
    if (first && recall.length) {
      fail(
        "recall-count",
        phase.id,
        `${label} is the first phase — there is nothing earlier to recall`,
      );
    }
    const sources = new Set();
    for (const r of recall) {
      const source = phaseOf.get(r.from);
      if (!source) {
        fail("recall-resolves", r.id, `recalls "${r.from}", which is not an objective anywhere`);
        continue;
      }
      if (source.num >= phase.num) {
        fail(
          "recall-is-earlier",
          r.id,
          `recalls "${r.from}" from phase ${source.num} — a recall check must reach backwards, not forwards`,
        );
        continue;
      }
      sources.add(source.num);
    }
    // Phase 2 is exempt: only phase 1 exists to draw from, so a spread is impossible.
    if (phase.num > 2 && recall.length && sources.size < 2) {
      fail(
        "recall-spread",
        phase.id,
        `${label} draws every recall check from phase ${[...sources][0]} — that is blocked practice, not interleaved`,
      );
    }

    for (const o of phase.objectives) {
      if (!taught.has(o.id)) {
        fail("objective-taught", o.id, `no concept card in ${label} teaches this objective`);
      }
      const level = levelOf(o.id);
      if (NEEDS_ARTIFACT.has(level) && !assessed.has(o.id)) {
        fail(
          "objective-assessed",
          o.id,
          `"${level}"-level objective is not assessed by any exercise or workshop in ${label}`,
        );
      }
      if (!NEEDS_ARTIFACT.has(level) && !assessed.has(o.id) && !(phase.checkpoint ?? []).length) {
        fail(
          "objective-assessed",
          o.id,
          "nothing assesses this objective, not even a checkpoint question",
        );
      }
    }

    if (!phase.workshop) fail("phase-has-workshop", phase.id, `${label} ends without a workshop`);
  }

  const counts = phases.reduce(
    (acc, p) => ({
      phases: acc.phases + 1,
      objectives: acc.objectives + p.objectives.length,
      concepts: acc.concepts + p.concepts.length,
      exercises: acc.exercises + p.exercises.length,
      blanks: acc.blanks + p.exercises.filter((e) => e.rung === "independent").length,
      recall: acc.recall + (p.recall?.length ?? 0),
      predicts:
        acc.predicts +
        p.concepts.reduce(
          (n, c) => n + (c.blocks ?? []).filter((b) => b.kind === "predict").length,
          0,
        ),
      workshops: acc.workshops + (p.workshop ? 1 : 0),
    }),
    {
      phases: 0,
      objectives: 0,
      concepts: 0,
      exercises: 0,
      blanks: 0,
      recall: 0,
      predicts: 0,
      workshops: 0,
    },
  );
  return { errors, counts };
}

/**
 * Splits violations into the ones that must fail the build and the known-gap
 * entries that no longer describe anything real. A stale entry is itself a
 * failure, which is what stops the list rotting into a permanent excuse file.
 */
export function sieve(errors, knownGaps) {
  const matches = (gap, e) => gap.rule === e.rule && gap.subject === e.subject;
  return {
    live: errors.filter((e) => !knownGaps.some((g) => matches(g, e))),
    stale: knownGaps.filter((g) => !errors.some((e) => matches(g, e))),
  };
}
