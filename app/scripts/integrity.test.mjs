/**
 * Proves every integrity rule actually fires.
 *
 * Same discipline as the other two suites: start from data that is well-formed,
 * break exactly one thing, and assert the matching rule complains. Run with
 * `pnpm test`.
 */
import assert from "node:assert/strict";
import { test } from "node:test";
import { audit } from "./lib/integrity.mjs";

/** A phase with nothing wrong with it; tests mutate one field at a time. */
const sound = (over = {}) => ({
  num: 1,
  id: "px",
  weeks: "Week 1",
  color: "#000",
  title: "Test phase",
  tagline: "t",
  tldr: "Short.",
  objectives: [{ id: "px-o1", text: "**Implement** the thing" }],
  concepts: [
    { id: "px-c1", title: "The thing", teaches: ["px-o1"], blocks: [{ kind: "p", text: "ok" }] },
  ],
  exercises: [
    { id: "px-e1", title: "Do it", task: "t", rung: "faded", assesses: ["px-o1"], solution: ["s"] },
  ],
  resources: [{ label: "Docs", url: "https://example.com/docs" }],
  ...over,
});

/** One card carrying the blocks under test. */
const carrying = (blocks) =>
  sound({ concepts: [{ id: "px-c1", title: "c", teaches: ["px-o1"], blocks }] });

const rules = (input) => audit(input).errors.map((e) => e.rule);
const phaseRules = (phase) => rules({ phases: [phase] });

test("well-formed data produces no complaints", () => {
  assert.deepEqual(phaseRules(sound()), []);
});

test("a duplicate id is caught, because ids are saved-progress keys", () => {
  const phase = sound({
    exercises: [
      { id: "px-e1", title: "e", task: "t", assesses: ["px-o1"], solution: ["s"] },
      { id: "px-e1", title: "clone", task: "t", assesses: ["px-o1"], solution: ["s"] },
    ],
  });
  assert.ok(phaseRules(phase).includes("id-unique"));
});

test("the q-bank, prerequisites and electives are in the uniqueness scan too", () => {
  // The alignment gate never walked these, so a collision here was invisible
  // despite being the same localStorage key it would have caught elsewhere.
  const qbank = sound({
    qbank: [{ group: "g", items: [{ id: "px-o1", q: "q", a: "a" }] }],
  });
  assert.ok(phaseRules(qbank).includes("id-unique"));

  const withIntro = {
    phases: [sound()],
    prerequisites: [{ id: "pre-1", text: "p" }],
    electives: [
      {
        id: "pre-1",
        title: "e",
        tag: "t",
        trigger: "when",
        cost: "a day",
        blocks: [],
        resources: [],
      },
    ],
  };
  assert.ok(rules(withIntro).includes("id-unique"));
});

test("an id that does not match the phase it lives in fails", () => {
  // The realistic version of this is a card copied between phase files, which
  // keeps its old prefix and is otherwise undetectable.
  const strays = sound({
    concepts: [
      { id: "p1-c9", title: "c", teaches: ["px-o1"], blocks: [{ kind: "p", text: "ok" }] },
    ],
  });
  assert.deepEqual(phaseRules(strays), ["id-prefix"]);
});

test("workshop and q-bank ids are exempt from the prefix rule", () => {
  const phase = sound({
    workshop: {
      id: "w1",
      title: "W",
      subtitle: "s",
      assesses: ["px-o1"],
      blocks: [],
      deliverables: [{ id: "w1-d1", text: "d", tier: "minimum" }],
    },
    qbank: [{ group: "g", items: [{ id: "qb-1", q: "q", a: "a" }] }],
  });
  // The tier rules fire too — this fixture is a one-item workshop on purpose.
  // Asserting the *absence* of the prefix rule keeps this test about its subject.
  assert.ok(!phaseRules(phase).includes("id-prefix"));
});

test("a block kind the density walk does not know fails", () => {
  // The failure this guards: a kind added to types.ts and to BlockList (which the
  // compiler enforces) but not to density.mjs, which would render it and measure
  // it as zero, so it escapes the budget in silence.
  assert.deepEqual(phaseRules(carrying([{ kind: "sidebar", text: "hi" }])), ["block-kind-known"]);
});

test("a ragged table row fails", () => {
  const table = (rows) => [{ kind: "table", headers: ["a", "b"], rows }];
  assert.deepEqual(phaseRules(carrying(table([["1", "2"]]))), []);
  assert.deepEqual(phaseRules(carrying(table([["1", "2"], ["1"]]))), ["table-shape"]);
  assert.deepEqual(phaseRules(carrying(table([["1", "2", "3"]]))), ["table-shape"]);
});

test("empty content that satisfies the type is still empty", () => {
  const cases = [
    [{ kind: "p", text: "  " }],
    [{ kind: "list", items: [] }],
    [{ kind: "list", items: ["ok", ""] }],
    [{ kind: "code", code: "" }],
    [{ kind: "callout", tone: "tip", title: "t", text: "" }],
    [{ kind: "flow", nodes: [] }],
    [{ kind: "flow", nodes: [{ label: "" }] }],
    [{ kind: "deepdive", title: "d", blocks: [] }],
    [{ kind: "predict", prompt: "p", answer: "a", consolidation: "" }],
  ];
  for (const blocks of cases) {
    assert.deepEqual(phaseRules(carrying(blocks)), ["empty-content"], JSON.stringify(blocks));
  }
});

test("an exercise with no solution notes and a workshop with no deliverables fail", () => {
  const noNotes = sound({
    exercises: [{ id: "px-e1", title: "e", task: "t", assesses: ["px-o1"], solution: [] }],
  });
  assert.deepEqual(phaseRules(noNotes), ["empty-content"]);

  const noDeliverables = sound({
    workshop: {
      id: "px-w",
      title: "W",
      subtitle: "s",
      assesses: ["px-o1"],
      blocks: [],
      deliverables: [],
    },
  });
  assert.deepEqual(phaseRules(noDeliverables), ["empty-content"]);
});

test("an elective without a trigger fails — that is the whole contract", () => {
  const elective = (over) => ({
    id: "el-x",
    title: "E",
    tag: "t",
    trigger: "when the job ad says so",
    cost: "a weekend",
    blocks: [],
    resources: [],
    ...over,
  });
  assert.deepEqual(rules({ phases: [sound()], electives: [elective()] }), []);
  assert.deepEqual(rules({ phases: [sound()], electives: [elective({ trigger: "" })] }), [
    "empty-content",
  ]);
  assert.deepEqual(rules({ phases: [sound()], electives: [elective({ cost: " " })] }), [
    "empty-content",
  ]);
});

test("a resource url that is not a followable link fails", () => {
  const withUrl = (url) => sound({ resources: [{ label: "Docs", url }] });
  assert.deepEqual(phaseRules(withUrl("https://example.com")), []);
  assert.deepEqual(phaseRules(withUrl("http://example.com")), []);
  assert.deepEqual(phaseRules(withUrl("/relative/path")), ["resource-url"]);
  assert.deepEqual(phaseRules(withUrl("exmaple.com/typo")), ["resource-url"]);
  assert.deepEqual(phaseRules(withUrl("javascript:alert(1)")), ["resource-url"]);
});

test("blocks inside a deep dive are held to the same rules as blocks outside", () => {
  const dive = [
    {
      kind: "deepdive",
      title: "The long way round",
      blocks: [{ kind: "table", headers: ["a", "b"], rows: [["only one"]] }],
    },
  ];
  assert.deepEqual(phaseRules(carrying(dive)), ["table-shape"]);
});

test("a repo path that is not on disk fails", () => {
  const phase = sound({
    exercises: [
      {
        id: "px-e1",
        title: "e",
        task: "t",
        repo: "phase0-nope",
        assesses: ["px-o1"],
        solution: ["s"],
      },
    ],
  });
  const { errors } = audit({ phases: [phase], repoExists: (r) => r === "workshops/assistant" });
  assert.ok(errors.some((e) => e.rule === "repo-exists" && e.subject === "px-e1"));
});

/** Four questions covering all four elements: the shape a real phase has to hit. */
const defended = (over = []) =>
  sound({
    checkpoint: over.length
      ? over
      : [
          { id: "px-q1", q: "q", a: "a", demands: ["alternatives", "constraints"] },
          { id: "px-q2", q: "q", a: "a", demands: ["evidence", "failure-modes"] },
        ],
  });

test("a sound phase with checkpoints passes the defense rules", () => {
  assert.deepEqual(phaseRules(defended()), []);
});

test("a checkpoint demanding one element fails — that is an explanation", () => {
  const phase = defended([
    { id: "px-q1", q: "q", a: "a", demands: ["alternatives"] },
    { id: "px-q2", q: "q", a: "a", demands: ["constraints", "evidence", "failure-modes"] },
  ]);
  assert.ok(phaseRules(phase).includes("defense-rubric"));
});

test("a checkpoint with no rubric at all fails the same way", () => {
  const phase = defended([
    { id: "px-q1", q: "q", a: "a" },
    { id: "px-q2", q: "q", a: "a", demands: ["constraints", "evidence", "failure-modes"] },
  ]);
  assert.ok(phaseRules(phase).includes("defense-rubric"));
});

test("a phase that never asks for failure modes fails, even with rich questions", () => {
  // The element candidates skip. A phase can look thorough and still let the
  // student practise the omission, which is exactly what coverage is for.
  const phase = defended([
    { id: "px-q1", q: "q", a: "a", demands: ["alternatives", "constraints"] },
    { id: "px-q2", q: "q", a: "a", demands: ["constraints", "evidence"] },
  ]);
  const errors = audit({ phases: [phase] }).errors;
  const coverage = errors.find((e) => e.rule === "defense-coverage");
  assert.ok(coverage, "expected a coverage complaint");
  assert.match(coverage.message, /failure-modes/);
});

test("an element outside the four is rejected rather than counted", () => {
  const phase = defended([
    { id: "px-q1", q: "q", a: "a", demands: ["alternatives", "vibes"] },
    { id: "px-q2", q: "q", a: "a", demands: ["constraints", "evidence", "failure-modes"] },
  ]);
  assert.ok(phaseRules(phase).includes("defense-elements"));
});

test("the same element twice does not satisfy the two-element floor", () => {
  const phase = defended([
    { id: "px-q1", q: "q", a: "a", demands: ["evidence", "evidence"] },
    { id: "px-q2", q: "q", a: "a", demands: ["alternatives", "constraints", "failure-modes"] },
  ]);
  const found = phaseRules(phase);
  assert.ok(found.includes("defense-elements"));
  assert.ok(found.includes("defense-rubric"));
});

test("a phase with no checkpoint is not held to coverage", () => {
  // Nothing to cover. Failing here would demand a checkpoint section from every
  // phase, which is a different rule and not this one's business.
  assert.deepEqual(phaseRules(sound()), []);
});

/** A workshop whose tiers are shaped the way the rules want. */
const tiered = (over = {}) => ({
  id: "w9",
  title: "W",
  subtitle: "s",
  proves: "integrate",
  assesses: ["px-o1"],
  blocks: [],
  deliverables: [
    { id: "w9-d1", text: "skeleton", tier: "minimum" },
    { id: "w9-d2", text: "skeleton", tier: "minimum" },
    { id: "w9-d3", text: "polish", tier: "full" },
    { id: "w9-d4", text: "polish", tier: "full" },
  ],
  stretch: ["go further"],
  ...over,
});

const tierRules = (workshop) =>
  phaseRules(sound({ workshop })).filter(
    (r) => r.startsWith("workshop-tiers") || r === "deliverable-tier",
  );

test("a well-tiered workshop passes", () => {
  assert.deepEqual(tierRules(tiered()), []);
});

test("a one-item minimum is not a walking skeleton", () => {
  const workshop = tiered({
    deliverables: [
      { id: "w9-d1", text: "skeleton", tier: "minimum" },
      { id: "w9-d2", text: "polish", tier: "full" },
      { id: "w9-d3", text: "polish", tier: "full" },
    ],
  });
  assert.deepEqual(tierRules(workshop), ["workshop-tiers"]);
});

test("a minimum that is most of the workshop is the full list with a nicer label", () => {
  // The failure mode the tiering exists to prevent, so it has to be caught rather
  // than trusted: relabelling everything "minimum" would pass a naive count check.
  const workshop = tiered({
    deliverables: [
      { id: "w9-d1", text: "a", tier: "minimum" },
      { id: "w9-d2", text: "b", tier: "minimum" },
      { id: "w9-d3", text: "c", tier: "minimum" },
      { id: "w9-d4", text: "d", tier: "full" },
    ],
  });
  const found = audit({ phases: [sound({ workshop })] }).errors;
  const tiers = found.find((e) => e.rule === "workshop-tiers");
  assert.ok(tiers);
  assert.match(tiers.message, /reassuring label/);
});

test("an all-minimum workshop says nothing with its tiers", () => {
  const workshop = tiered({
    deliverables: [
      { id: "w9-d1", text: "a", tier: "minimum" },
      { id: "w9-d2", text: "b", tier: "minimum" },
    ],
  });
  assert.ok(tierRules(workshop).includes("workshop-tiers"));
});

test("a tier outside the two is rejected", () => {
  const workshop = tiered({
    deliverables: [
      { id: "w9-d1", text: "a", tier: "minimum" },
      { id: "w9-d2", text: "b", tier: "minimum" },
      { id: "w9-d3", text: "c", tier: "someday" },
      { id: "w9-d4", text: "d", tier: "full" },
    ],
  });
  assert.ok(tierRules(workshop).includes("deliverable-tier"));
});

test("a workshop with no stretch tier fails", () => {
  assert.ok(tierRules(tiered({ stretch: [] })).includes("workshop-tiers"));
});
