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

/**
 * The mastery ladder, ordered. See `Mastery` in data/types.ts for what each
 * level means; the index is what makes "at least this high" comparable.
 */
export const MASTERY = ["understand", "implement", "integrate", "operate"];
export const RANK = new Map(MASTERY.map((level, i) => [level, i]));

/**
 * Words that turn "it works" into a number somebody else could check.
 *
 * `operate` is the top of the ladder and it means the reader ran the thing and
 * knows what it did — which is only distinguishable from `integrate` by a
 * measurement. The audit that added this rule found a blank-editor agent exercise
 * claiming `operate` whose whole verification was "confirm it terminates and says
 * so": true of a loop stopped by its cap, of one stopped by its deadline, and of
 * one where the model happened to give up before either limit was reached. Three
 * different systems, one indistinguishable sentence, and only a step count and an
 * elapsed time can tell them apart.
 *
 * Deliberately a word list and not a judgement. A gate that tried to assess
 * whether a task's verification was rigorous would be a language model with a
 * false-positive rate; this one asks the narrower question of whether the task
 * asks for a number at all, which is mechanical, and leaves the rest to review.
 */
export const MEASUREMENT_WORDS = [
  "measure",
  "record",
  "count",
  "elapsed",
  "latency",
  "percentile",
  "p95",
  "p99",
  "throughput",
  "budget",
  "number",
  "numbers",
  "table of numbers",
  "before and after",
  "how many",
  "how long",
  "seconds",
  "tokens",
  "cost",
  "rate",
  "score",
];

/**
 * Every piece of PROSE a task addresses to its reader.
 *
 * Exercises carry theirs in `task` and `solution`; workshops have neither and
 * carry theirs in `blocks`. Both are collected, and `code` blocks are deliberately
 * not: a reference implementation that happens to contain a variable called
 * `score` would satisfy the rule below without ever asking the reader for
 * anything, and a gate with that hole is a gate authors learn to feed.
 */
function proseOf(item) {
  const parts = [item.task ?? "", ...(item.solution ?? [])];
  // A workshop's real "done when" list. This is where an `operate` workshop says
  // what the reader must be holding at the end, so it is exactly where a demand
  // for numbers belongs.
  for (const deliverable of item.deliverables ?? []) parts.push(deliverable.text ?? "");
  for (const block of item.blocks ?? []) {
    if (block.kind === "code") continue;
    parts.push(block.title ?? "", block.text ?? "");
    for (const node of block.nodes ?? []) parts.push(node.label ?? "", node.sub ?? "");
    for (const row of block.items ?? []) parts.push(typeof row === "string" ? row : "");
  }
  return parts.join(" ").toLowerCase();
}

/** Whether a task asks its reader to come away holding a number. */
export function demandsAMeasurement(item) {
  const prose = proseOf(item);
  return MEASUREMENT_WORDS.some((word) => prose.includes(word));
}

/**
 * The mastery floor each objective verb demands.
 *
 * Keyed by **verb**, not by Bloom level, and the difference is the whole point.
 * Bloom ranks how hard the thinking is; the ladder ranks what the finished work
 * demonstrates, and the two come apart badly at the top. "Design a system out
 * loud under interview pressure" is Bloom's `create` and produces an argument,
 * not a running service — mapping the whole `create` class to `operate` would
 * demand a deploy for a whiteboard exercise, and the gate would be wrong in a
 * way that teaches authors to game it. Meanwhile `consume`, a mere `apply`
 * verb, means talking to somebody else's server, which is squarely `integrate`.
 *
 * So each verb is placed by what it commits the course to. A missing verb is a
 * failure rather than a default: an unclassified verb would silently pass every
 * objective that used it, which is the one bug a gate must not have.
 *
 * A task ABOVE its objective's floor is fine and common — an objective is a
 * minimum, and a workshop routinely exceeds one. Only falling short is a
 * defect, because that is the course promising a level it never asks for.
 */
export const MASTERY_FLOOR = {
  // An explanation is proven by answering, arguing or choosing — not by a repo.
  define: "understand",
  list: "understand",
  name: "understand",
  recall: "understand",
  identify: "understand",
  explain: "understand",
  describe: "understand",
  summarize: "understand",
  contrast: "understand",
  classify: "understand",
  interpret: "understand",
  justify: "understand",
  critique: "understand",
  defend: "understand",
  judge: "understand",
  choose: "understand",
  evaluate: "understand",
  design: "understand",
  rehearse: "understand",
  // A working thing, in isolation, with its tests green.
  implement: "implement",
  build: "implement",
  run: "implement",
  use: "implement",
  construct: "implement",
  engineer: "implement",
  constrain: "implement",
  compose: "implement",
  rewrite: "implement",
  // Needs a system with parts that can disagree. You cannot diagnose, compare,
  // calibrate or measure something you have only built in isolation, and you
  // cannot consume a server you also wrote the client contract for.
  consume: "integrate",
  diagnose: "integrate",
  compare: "integrate",
  analyze: "integrate",
  differentiate: "integrate",
  audit: "integrate",
  measure: "integrate",
  estimate: "integrate",
  calibrate: "integrate",
  orchestrate: "integrate",
  combine: "integrate",
  // Only true once it is running under conditions that can hurt it. Each of
  // these names an act performed on a live system, so the assessment has to
  // produce evidence rather than a passing test.
  deploy: "operate",
  containerize: "operate",
  instrument: "operate",
  optimize: "operate",
  gate: "operate",
  contain: "operate",
};

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
    // Highest mastery any task claims for each objective, so the floor check
    // below asks "did ANYTHING reach this level" rather than penalising a phase
    // for also having a gentler warm-up exercise on the same objective.
    const provenFor = new Map();
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
        const claimed = RANK.get(item.proves);
        if (claimed !== undefined) {
          provenFor.set(ref, Math.max(provenFor.get(ref) ?? -1, claimed));
        }
      }
      if (!RANK.has(item.proves)) {
        fail(
          "mastery-declared",
          item.id,
          `${what} declares proves="${item.proves ?? ""}" — must be one of ${MASTERY.join(", ")}`,
        );
      }
      if (item.proves === "operate" && !demandsAMeasurement(item)) {
        fail(
          "operate-demands-numbers",
          item.id,
          `${what} claims proves="operate" but asks for no measurement — an operate task must ` +
            `require numbers (${MEASUREMENT_WORDS.join(", ")}), because "confirm it works" is a ` +
            "claim the reader grades themselves",
        );
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
      // The mastery gate. An objective is a promise written in a verb; this asks
      // whether anything the student is actually set reaches that high.
      const verb = leadVerb(o.text);
      const floor = MASTERY_FLOOR[verb ?? ""];
      if (verb && LEVEL_OF.has(verb) && !floor) {
        fail(
          "mastery-floor",
          o.id,
          `"${verb}" has no mastery floor — classify it in MASTERY_FLOOR, because an ` +
            "unclassified verb passes silently and a gate with a silent pass is not a gate",
        );
      }
      const reached = provenFor.get(o.id);
      if (floor && assessed.has(o.id) && reached !== undefined && reached < RANK.get(floor)) {
        fail(
          "mastery-floor",
          o.id,
          `"${verb}" promises ${floor}, but the tasks assessing it only reach ` +
            `${MASTERY[reached]} — either weaken the verb or set work that gets there`,
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
      operates:
        acc.operates +
        [...p.exercises, ...(p.workshop ? [p.workshop] : [])].filter((t) => t.proves === "operate")
          .length,
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
      operates: 0,
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
