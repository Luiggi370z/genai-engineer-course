import type { Block, Phase } from "../data/types";

/**
 * Adult silent reading of technical prose sits around 200–250 wpm. 220 is the
 * middle of that, and the tilde in front of the rendered number is doing honest
 * work — this is an estimate, not a promise.
 */
const WORDS_PER_MINUTE = 220;

/**
 * How long the phase takes to *read*, computed rather than authored.
 *
 * A number typed into the content files would be wrong the first time a card was
 * edited and nobody would notice; this one cannot drift.
 *
 * What counts is the first pass: objectives, the concept cards, the worked example.
 * What does not: code listings (skimmed, not read at prose speed), anything behind
 * a click — a deep dive, a predict answer, a question's answer — and the exercises
 * and workshop, because those are the work, not the reading. Under-counting is the
 * safer direction here: the label already tells the student the doing takes weeks.
 */
export function readingMinutes(phase: Phase): number {
  const text = [
    phase.tagline,
    phase.tldr,
    ...phase.objectives.map((o) => o.text),
    ...phase.concepts.flatMap((c) => visibleProse(c.blocks)),
    phase.example?.text ?? "",
  ].join(" ");
  return Math.max(1, Math.round(countWords(text) / WORDS_PER_MINUTE));
}

/** Kept in step with the `visibleProse` walk in `scripts/lib/density.mjs`. */
function visibleProse(blocks: Block[]): string[] {
  return blocks.flatMap(proseOf);
}

function proseOf(block: Block): string[] {
  switch (block.kind) {
    case "p":
      return [block.text];
    case "list":
      return block.items;
    case "callout":
      return [block.title, block.text];
    case "table":
      return [...block.headers, ...block.rows.flat()];
    case "flow":
      return block.nodes.map((node) => `${node.label} ${node.sub ?? ""}`);
    case "predict":
      return [block.prompt];
    case "code":
    case "deepdive":
      return [];
  }
}

function countWords(text: string): number {
  const plain = text.replace(/[*`]/g, " ");
  const words = plain.split(/\s+/).filter(Boolean);
  return words.length;
}
