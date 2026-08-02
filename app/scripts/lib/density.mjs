/**
 * The readability rules, as a pure function over course data.
 *
 * Separate from `alignment.mjs` because the concerns are different: alignment asks
 * whether a phase teaches what it tests, density asks whether a human can get
 * through the card without their eyes sliding off it. A card can be perfectly
 * aligned and still be a wall.
 *
 * Kept pure so `density.test.mjs` can feed it synthetic cards and prove each rule
 * fires. A gate nobody has seen fail is not a gate.
 */

/**
 * Every cap, in one place, with the measurement that produced it.
 *
 * These were set from the course as it stood, not from a style guide: the point was
 * to bite on the genuine outliers without turning the whole workbook into a rewrite.
 */
export const LIMITS = {
  /** ~70 words. Six lines at the 50–75-character measure the audit recommends. */
  paragraph: 450,
  /**
   * Visible prose per card, measured on the walk below: p50 1507, p90 2793, max 4265.
   *
   * Lower than the 3500 the plan quoted because that figure counted a predict
   * block's answer and consolidation, which a student only ever sees after choosing
   * to see them. Excluding them moved two cards — `p-evals-c1` and `p-memory-c2` —
   * out of the tail, and correctly so: their bulk was already behind a click, which
   * is the same reason deep dives do not count. 3000 keeps the rule biting on the
   * four cards that really are walls.
   */
  cardProse: 3000,
  /** Visible blocks per card. p50 was 4. */
  cardBlocks: 7,
  /** A deep dive is an escape valve, not an annexe. */
  deepDiveProse: 2500,
  /** A TL;DR you cannot read in one breath is not a TL;DR. */
  tldr: 300,
};

/** A cycle needs enough nodes to be a ring; a decision needs something to choose. */
export const SHAPE_MINIMUM = { cycle: 3, decision: 2 };

/**
 * What each block kind contributes to the text a student sees without clicking.
 *
 * Code is out because it is read at a different speed and in a different way, and
 * a long listing is not the failure mode this budget exists to catch. Deep dives
 * are out because excluding them is the entire mechanism — they are what an
 * over-budget card is supposed to be fixed *with*. Anything behind a disclosure
 * follows the same logic: a predict block's prompt counts, its answer does not.
 *
 * A table rather than a `switch` so the set of kinds is a value. The renderers
 * that do this in TypeScript get exhaustiveness from the compiler — `BlockList`
 * has a `never` check and `reading-time.ts` has no `default` — but this file is
 * plain JS, so a kind added to `types.ts` and forgotten here would simply measure
 * as zero and slip the budget in silence. `KNOWN_KINDS` is what the integrity
 * gate's `block-kind-known` rule reads to make that impossible.
 *
 * Kept in step with `proseOf` in `src/lib/reading-time.ts`.
 */
const PROSE_OF = {
  p: (block) => [block.text],
  list: (block) => block.items,
  callout: (block) => [block.title, block.text],
  table: (block) => [...block.headers, ...block.rows.flat()],
  flow: (block) => block.nodes.flatMap((node) => [node.label, node.sub ?? ""]),
  predict: (block) => [block.prompt],
  code: () => [],
  deepdive: () => [],
  // Chrome, not reading. Counting citation lines against a card's prose budget
  // would make citing a source cost you words you could have spent teaching.
  sources: () => [],
};

/** Every block kind this walk has an opinion about, derived from the table itself. */
export const KNOWN_KINDS = new Set(Object.keys(PROSE_OF));

export function visibleProse(blocks = []) {
  return blocks.flatMap((block) => PROSE_OF[block.kind]?.(block) ?? []);
}

const proseLength = (blocks) => visibleProse(blocks).join(" ").length;

/**
 * @param {object} input
 * @param {any[]} input.phases course data, in order
 * @returns {{ errors: {rule: string, subject: string, message: string}[], counts: object }}
 */
export function audit({ phases }) {
  const errors = [];
  const fail = (rule, subject, message) => errors.push({ rule, subject, message });
  const cardProse = [];

  for (const phase of phases) {
    if ((phase.tldr ?? "").length > LIMITS.tldr) {
      fail(
        "tldr-length",
        phase.id,
        `TL;DR is ${phase.tldr.length} chars, over the ${LIMITS.tldr} cap — cut it to the one thing the phase is about`,
      );
    }

    // Paragraph length and flow shapes apply everywhere blocks are rendered; a wall
    // of text is a wall wherever it stands. The per-card budgets below are narrower,
    // because a workshop brief is a spec you work from rather than prose you read
    // straight through, and holding it to a reading cap would be measuring the wrong
    // thing.
    const owners = [
      ...phase.concepts.map((c) => ({ id: c.id, blocks: c.blocks ?? [], card: true })),
      ...(phase.workshop
        ? [{ id: phase.workshop.id, blocks: phase.workshop.blocks ?? [], card: false }]
        : []),
    ];

    for (const owner of owners) {
      walk(owner.blocks, owner.id, fail, 0);

      if (!owner.card) continue;

      const prose = proseLength(owner.blocks);
      cardProse.push(prose);
      if (prose > LIMITS.cardProse) {
        fail(
          "card-prose",
          owner.id,
          `${prose} chars of visible prose, over the ${LIMITS.cardProse} cap — move the tail into a deep dive or cut it`,
        );
      }
      // Citations do not count against the cap. The budget exists to stop a card
      // carrying three ideas, and a source line is not an idea — charging for one
      // would make citing a number cost you a paragraph, which is a strange thing
      // for a workbook about evidence to price that way.
      const counted = owner.blocks.filter((b) => b.kind !== "sources");
      if (counted.length > LIMITS.cardBlocks) {
        fail(
          "card-blocks",
          owner.id,
          `${counted.length} visible blocks, over the ${LIMITS.cardBlocks} cap — this is two cards wearing a trenchcoat`,
        );
      }

      const dives = owner.blocks.filter((b) => b.kind === "deepdive");
      if (dives.length > 1) {
        fail(
          "deepdive-per-card",
          owner.id,
          `${dives.length} deep dives on one card — if this much is optional, the card is about the wrong thing`,
        );
      }
      for (const dive of dives) {
        const inside = proseLength(dive.blocks ?? []);
        if (inside > LIMITS.deepDiveProse) {
          fail(
            "deepdive-prose",
            owner.id,
            `deep dive "${dive.title}" holds ${inside} chars, over the ${LIMITS.deepDiveProse} cap — collapsing something is not the same as earning it`,
          );
        }
      }
    }
  }

  cardProse.sort((a, b) => a - b);
  const counts = {
    cards: cardProse.length,
    medianProse: cardProse.length ? (cardProse[Math.floor(cardProse.length / 2)] ?? 0) : 0,
    maxProse: cardProse.length ? (cardProse[cardProse.length - 1] ?? 0) : 0,
    deepDives: phases.reduce(
      (n, p) => n + p.concepts.reduce((m, c) => m + (c.blocks ?? []).filter(isDeepDive).length, 0),
      0,
    ),
    shaped: phases.reduce(
      (n, p) =>
        n +
        p.concepts.reduce(
          (m, c) =>
            m +
            (c.blocks ?? []).filter((b) => b.kind === "flow" && b.shape && b.shape !== "linear")
              .length,
          0,
        ),
      0,
    ),
  };
  return { errors, counts };
}

const isDeepDive = (block) => block.kind === "deepdive";

/** Recurses so a rule that applies to a block applies inside a deep dive too. */
function walk(blocks, subject, fail, depth) {
  for (const block of blocks ?? []) {
    if (block.kind === "p" && block.text.length > LIMITS.paragraph) {
      fail(
        "paragraph-length",
        subject,
        `a paragraph runs ${block.text.length} chars, over the ${LIMITS.paragraph} cap — split it or make it a list: "${block.text.slice(0, 48)}…"`,
      );
    }
    if (block.kind === "flow") {
      const minimum = SHAPE_MINIMUM[block.shape ?? "linear"];
      if (minimum && block.nodes.length < minimum) {
        fail(
          "flow-shape-nodes",
          subject,
          `a "${block.shape}" flow has ${block.nodes.length} node(s); it needs at least ${minimum} to be one`,
        );
      }
    }
    if (isDeepDive(block)) {
      if (depth > 0) {
        fail(
          "deepdive-depth",
          subject,
          `deep dive "${block.title}" is nested inside another — one click to opt in, never two`,
        );
      }
      walk(block.blocks, subject, fail, depth + 1);
    }
  }
}
