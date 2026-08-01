/**
 * Proves every density rule actually fires.
 *
 * Same discipline as `alignment.test.mjs`: start from a phase that is inside every
 * budget, break exactly one thing, and assert the matching rule complains. Run with
 * `pnpm test`.
 */
import assert from "node:assert/strict";
import { test } from "node:test";
import { audit, LIMITS } from "./lib/density.mjs";

/** Filler of an exact length, so a test states the limit it is crossing. */
const chars = (n) => "x".repeat(n);

/** A phase comfortably inside every budget; tests mutate one field at a time. */
const lean = (over = {}) => ({
  num: 1,
  id: "px",
  weeks: "Week 1",
  color: "#000",
  title: "Test phase",
  tagline: "t",
  tldr: "Short enough to read in a breath.",
  objectives: [{ id: "px-o1", text: "**Implement** the thing" }],
  concepts: [{ id: "px-c1", title: "c", teaches: ["px-o1"], blocks: [{ kind: "p", text: "ok" }] }],
  exercises: [],
  resources: [],
  ...over,
});

/** One card, with the blocks under test. */
const carrying = (blocks) => lean({ concepts: [{ id: "px-c1", title: "c", blocks }] });

const rules = (phases) => audit({ phases }).errors.map((e) => e.rule);

test("a phase inside every budget produces no complaints", () => {
  assert.deepEqual(rules([lean()]), []);
});

test("a paragraph over the cap fails", () => {
  assert.deepEqual(rules([carrying([{ kind: "p", text: chars(LIMITS.paragraph) }])]), []);
  assert.deepEqual(rules([carrying([{ kind: "p", text: chars(LIMITS.paragraph + 1) }])]), [
    "paragraph-length",
  ]);
});

test("a card over the prose cap fails", () => {
  const blocks = [
    { kind: "p", text: chars(LIMITS.cardProse) },
    { kind: "list", items: ["and some more"] },
  ];
  assert.ok(rules([carrying(blocks)]).includes("card-prose"));
});

test("code and deep dives do not count against the card's prose", () => {
  const blocks = [
    { kind: "code", code: chars(LIMITS.cardProse * 2) },
    {
      kind: "deepdive",
      title: "The long way round",
      blocks: [{ kind: "p", text: chars(LIMITS.paragraph) }],
    },
  ];
  assert.deepEqual(rules([carrying(blocks)]), []);
});

test("a predict block's answer is not counted, but its prompt is", () => {
  const predict = (promptLength) => [
    {
      kind: "predict",
      prompt: chars(promptLength),
      answer: chars(LIMITS.cardProse),
      consolidation: chars(LIMITS.cardProse),
    },
  ];
  assert.deepEqual(rules([carrying(predict(10))]), []);
  assert.ok(rules([carrying(predict(LIMITS.cardProse + 1))]).includes("card-prose"));
});

test("a card over the block cap fails", () => {
  const blocks = Array.from({ length: LIMITS.cardBlocks + 1 }, () => ({ kind: "p", text: "ok" }));
  assert.ok(rules([carrying(blocks)]).includes("card-blocks"));
  assert.deepEqual(rules([carrying(blocks.slice(1))]), []);
});

test("a second deep dive on one card fails", () => {
  const dive = (title) => ({ kind: "deepdive", title, blocks: [{ kind: "p", text: "ok" }] });
  assert.deepEqual(rules([carrying([dive("one")])]), []);
  assert.deepEqual(rules([carrying([dive("one"), dive("two")])]), ["deepdive-per-card"]);
});

test("a deep dive nested inside a deep dive fails", () => {
  const nested = {
    kind: "deepdive",
    title: "outer",
    blocks: [{ kind: "deepdive", title: "inner", blocks: [{ kind: "p", text: "ok" }] }],
  };
  assert.deepEqual(rules([carrying([nested])]), ["deepdive-depth"]);
});

test("a deep dive over its own prose cap fails — collapsing is not a licence", () => {
  const stuffed = {
    kind: "deepdive",
    title: "everything I could not bear to cut",
    blocks: [
      { kind: "list", items: [chars(LIMITS.deepDiveProse), "and more"] },
      { kind: "p", text: "ok" },
    ],
  };
  assert.ok(rules([carrying([stuffed])]).includes("deepdive-prose"));
});

test("a TL;DR over the cap fails", () => {
  assert.deepEqual(rules([lean({ tldr: chars(LIMITS.tldr) })]), []);
  assert.deepEqual(rules([lean({ tldr: chars(LIMITS.tldr + 1) })]), ["tldr-length"]);
});

test("a cycle needs three nodes and a decision needs two", () => {
  const flow = (shape, count) => [
    { kind: "flow", shape, nodes: Array.from({ length: count }, (_, i) => ({ label: `n${i}` })) },
  ];
  assert.deepEqual(rules([carrying(flow("cycle", 2))]), ["flow-shape-nodes"]);
  assert.deepEqual(rules([carrying(flow("cycle", 3))]), []);
  assert.deepEqual(rules([carrying(flow("decision", 1))]), ["flow-shape-nodes"]);
  assert.deepEqual(rules([carrying(flow("decision", 2))]), []);
  // A linear flow is the default and has no minimum: a two-step pipeline is a
  // pipeline, and a one-node one is a label, not a lie about its shape.
  assert.deepEqual(rules([carrying(flow("linear", 1))]), []);
});

test("workshop blocks are held to paragraph length but not to the card budgets", () => {
  const workshop = {
    id: "px-w",
    title: "W",
    subtitle: "s",
    blocks: [
      { kind: "p", text: chars(LIMITS.paragraph + 1) },
      { kind: "list", items: [chars(LIMITS.cardProse)] },
    ],
    deliverables: [],
  };
  assert.deepEqual(rules([lean({ workshop })]), ["paragraph-length"]);
});
