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
      deliverables: [{ id: "w1-d1", text: "d" }],
    },
    qbank: [{ group: "g", items: [{ id: "qb-1", q: "q", a: "a" }] }],
  });
  assert.deepEqual(phaseRules(phase), []);
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
