/**
 * Proves every alignment rule actually fires.
 *
 * A gate nobody has watched fail is decoration, so each test starts from an
 * aligned phase, breaks exactly one thing, and asserts the matching rule
 * complains. Run with `pnpm test` (node's built-in runner, no dependencies).
 */
import assert from "node:assert/strict";
import { test } from "node:test";
import { audit, sieve } from "./lib/alignment.mjs";

/**
 * A minimal phase that satisfies every rule; tests mutate one field at a time.
 *
 * It carries two exercises because the ladder requires it: one faded rung and one
 * independent. A fixture that could not pass `independent-per-phase` would make
 * every other test in this file assert against a phase the real checker rejects.
 */
const aligned = (over = {}) => ({
  num: 1,
  id: "px",
  weeks: "Week 1",
  color: "#000",
  title: "Test phase",
  tagline: "t",
  objectives: [{ id: "px-o1", text: "**Implement** the thing" }],
  concepts: [{ id: "px-c1", title: "The thing", teaches: ["px-o1"], blocks: [] }],
  exercises: [
    { id: "px-e1", title: "Do it", task: "t", rung: "faded", assesses: ["px-o1"], solution: [] },
    {
      id: "px-e2",
      title: "From scratch",
      task: "t",
      rung: "independent",
      assesses: ["px-o1"],
      solution: [],
    },
  ],
  workshop: {
    id: "px-w",
    title: "W",
    subtitle: "s",
    repo: "workshops/assistant",
    assesses: ["px-o1"],
    blocks: [],
    deliverables: [{ id: "px-w-d1", text: "d" }],
  },
  checkpoint: [{ id: "px-q1", q: "q", a: "a" }],
  resources: [],
  ...over,
});

/** The same, at an arbitrary position in the course, for the recall rules. */
const at = (num, id, over = {}) =>
  aligned({
    num,
    id,
    objectives: [{ id: `${id}-o1`, text: "**Implement** the thing" }],
    concepts: [{ id: `${id}-c1`, title: "c", teaches: [`${id}-o1`], blocks: [] }],
    exercises: [
      {
        id: `${id}-e1`,
        title: "e",
        task: "t",
        rung: "faded",
        assesses: [`${id}-o1`],
        solution: [],
      },
      {
        id: `${id}-e2`,
        title: "b",
        task: "t",
        rung: "independent",
        assesses: [`${id}-o1`],
        solution: [],
      },
    ],
    workshop: {
      id: `${id}-w`,
      title: "W",
      subtitle: "s",
      repo: "workshops/assistant",
      assesses: [`${id}-o1`],
      blocks: [],
      deliverables: [{ id: `${id}-w-d1`, text: "d" }],
    },
    checkpoint: [{ id: `${id}-q1`, q: "q", a: "a" }],
    ...over,
  });

const recallOf = (id, ...froms) =>
  froms.map((from, i) => ({ id: `${id}-r${i + 1}`, q: "q", a: "a", from }));

const rules = (phases) => audit({ phases }).errors.map((e) => e.rule);

test("an aligned phase produces no complaints", () => {
  assert.deepEqual(rules([aligned()]), []);
});

test("an exercise testing an untaught skill fails — the whole point", () => {
  const phase = aligned({
    objectives: [
      { id: "px-o1", text: "**Implement** the thing" },
      { id: "px-o2", text: "**Diagnose** the other thing" },
    ],
    exercises: [
      { id: "px-e1", title: "Do it", task: "t", assesses: ["px-o1", "px-o2"], solution: [] },
    ],
  });
  const found = rules([phase]);
  assert.ok(
    found.includes("taught-before-tested"),
    "no card teaches px-o2, yet an exercise tests it",
  );
  assert.ok(found.includes("objective-taught"));
});

test("an objective nothing assesses fails when it is above understand level", () => {
  const phase = aligned({
    objectives: [{ id: "px-o1", text: "**Engineer** the thing" }],
    exercises: [],
    workshop: undefined,
  });
  assert.ok(rules([phase]).includes("objective-assessed"));
});

test("an understand-level objective may lean on the checkpoint instead", () => {
  const phase = aligned({
    objectives: [
      { id: "px-o1", text: "**Explain** the thing" },
      { id: "px-o2", text: "**Build** the other thing" },
    ],
    concepts: [{ id: "px-c1", title: "c", teaches: ["px-o1", "px-o2"], blocks: [] }],
    exercises: [
      { id: "px-e1", title: "e", task: "t", rung: "faded", assesses: ["px-o2"], solution: [] },
      {
        id: "px-e2",
        title: "b",
        task: "t",
        rung: "independent",
        assesses: ["px-o2"],
        solution: [],
      },
    ],
  });
  assert.deepEqual(rules([phase]), []);
});

test("an objective with no Bloom verb fails, and so does an unknown one", () => {
  assert.ok(
    rules([aligned({ objectives: [{ id: "px-o1", text: "Get good at the thing" }] })]).includes(
      "bloom-verb",
    ),
  );
  assert.ok(
    rules([aligned({ objectives: [{ id: "px-o1", text: "**Vibe** the thing" }] })]).includes(
      "bloom-verb",
    ),
  );
});

test("a phase that never rises above recall is flagged as a reading", () => {
  const phase = aligned({
    objectives: [{ id: "px-o1", text: "**Name** the thing" }],
    exercises: [],
    workshop: undefined,
  });
  assert.ok(rules([phase]).includes("phase-depth"));
});

test("a prerequisite from a later phase fails", () => {
  const first = aligned();
  const second = aligned({
    num: 2,
    id: "py",
    objectives: [{ id: "py-o1", text: "**Build** more" }],
    concepts: [{ id: "py-c1", title: "c", teaches: ["py-o1"], blocks: [] }],
    exercises: [
      { id: "py-e1", title: "e", task: "t", assesses: ["py-o1"], needs: ["pz-o1"], solution: [] },
    ],
    workshop: undefined,
    checkpoint: [{ id: "py-q1", q: "q", a: "a" }],
  });
  const third = aligned({
    num: 3,
    id: "pz",
    objectives: [{ id: "pz-o1", text: "**Build** last" }],
    concepts: [{ id: "pz-c1", title: "c", teaches: ["pz-o1"], blocks: [] }],
    exercises: [{ id: "pz-e1", title: "e", task: "t", assesses: ["pz-o1"], solution: [] }],
    workshop: undefined,
    checkpoint: [{ id: "pz-q1", q: "q", a: "a" }],
  });
  const found = rules([first, second, third]);
  assert.ok(found.includes("needs-is-earlier"), "phase 2 cannot require what phase 3 teaches");
  assert.ok(!found.includes("needs-resolves"), "the id does exist, it is just in the wrong place");
});

test("a dangling reference fails whichever side it is on", () => {
  assert.ok(
    rules([
      aligned({ concepts: [{ id: "px-c1", title: "c", teaches: ["nope"], blocks: [] }] }),
    ]).includes("teaches-resolves"),
  );
  assert.ok(
    rules([
      aligned({
        exercises: [{ id: "px-e1", title: "e", task: "t", assesses: ["nope"], solution: [] }],
      }),
    ]).includes("assesses-resolves"),
  );
  assert.ok(
    rules([
      aligned({
        exercises: [
          {
            id: "px-e1",
            title: "e",
            task: "t",
            assesses: ["px-o1"],
            needs: ["nope"],
            solution: [],
          },
        ],
      }),
    ]).includes("needs-resolves"),
  );
});

test("a card that teaches nothing and a task that tests nothing both fail", () => {
  assert.ok(
    rules([aligned({ concepts: [{ id: "px-c1", title: "c", teaches: [], blocks: [] }] })]).includes(
      "concept-teaches",
    ),
  );
  assert.ok(
    rules([
      aligned({ exercises: [{ id: "px-e1", title: "e", task: "t", assesses: [], solution: [] }] }),
    ]).includes("assesses-present"),
  );
});

// Duplicate ids and missing repo paths were once checked here. They are questions
// about well-formedness rather than about alignment, so both the rules and their
// tests now live in `integrity.test.mjs`.

test("a phase without a workshop is flagged", () => {
  assert.ok(rules([aligned({ workshop: undefined })]).includes("phase-has-workshop"));
});

test("a phase whose hardest task still ships a scaffold is flagged", () => {
  const phase = aligned({
    exercises: [
      { id: "px-e1", title: "e", task: "t", rung: "faded", assesses: ["px-o1"], solution: [] },
    ],
  });
  assert.ok(
    rules([phase]).includes("independent-per-phase"),
    "every phase needs one rung with nothing to fill in",
  );
});

test("an independent task may not hand back a reference implementation or a repo", () => {
  const withCode = aligned({
    exercises: [
      {
        id: "px-e1",
        title: "e",
        task: "t",
        rung: "independent",
        assesses: ["px-o1"],
        solution: [],
        code: "print('here you go')",
      },
    ],
  });
  assert.ok(rules([withCode]).includes("independent-has-no-code"));

  const withRepo = aligned({
    exercises: [
      {
        id: "px-e1",
        title: "e",
        task: "t",
        rung: "independent",
        repo: "workshops/assistant",
        assesses: ["px-o1"],
        solution: [],
      },
    ],
  });
  assert.ok(
    rules([withRepo]).includes("independent-has-no-code"),
    "a repo to clone is a scaffold by another name",
  );
});

test("a phase after the first needs three recall checks, and the first needs none", () => {
  const thin = rules([at(1, "px"), at(2, "py", { recall: recallOf("py", "px-o1") })]);
  assert.ok(thin.includes("recall-count"), "one check is not a warm-up");

  const backwards = rules([at(1, "px", { recall: recallOf("px", "px-o1") })]);
  assert.ok(backwards.includes("recall-count"), "nothing precedes phase 1");
});

test("a recall check must point at a real objective, and an earlier one", () => {
  const dangling = rules([
    at(1, "px"),
    at(2, "py", { recall: recallOf("py", "nope", "nope2", "nope3") }),
  ]);
  assert.ok(dangling.includes("recall-resolves"));

  const forwards = rules([
    at(1, "px"),
    at(2, "py", { recall: recallOf("py", "pz-o1", "pz-o1", "pz-o1") }),
    at(3, "pz"),
  ]);
  assert.ok(
    forwards.includes("recall-is-earlier"),
    "you cannot recall what you have not been taught",
  );
});

test("three checks from one earlier phase is blocked practice, not interleaved", () => {
  const blocked = rules([
    at(1, "px"),
    at(2, "py", { recall: recallOf("py", "px-o1", "px-o1", "px-o1") }),
    at(3, "pz", { recall: recallOf("pz", "py-o1", "py-o1", "py-o1") }),
  ]);
  assert.ok(blocked.includes("recall-spread"));

  const mixed = rules([
    at(1, "px"),
    at(2, "py", { recall: recallOf("py", "px-o1", "px-o1", "px-o1") }),
    at(3, "pz", { recall: recallOf("pz", "px-o1", "py-o1", "py-o1") }),
  ]);
  assert.ok(
    !mixed.includes("recall-spread"),
    "phase 2 is exempt — only phase 1 exists for it to draw from",
  );
});

test("a known gap silences its own violation and nothing else", () => {
  const phase = aligned({ workshop: undefined });
  const { errors } = audit({ phases: [phase] });
  const { live, stale } = sieve(errors, [
    { rule: "phase-has-workshop", subject: "px", why: "w", closedBy: "task X" },
  ]);
  assert.deepEqual(live, []);
  assert.deepEqual(stale, []);
});

test("a known gap that has been fixed goes stale and still fails the build", () => {
  const { errors } = audit({ phases: [aligned()] });
  const { live, stale } = sieve(errors, [
    { rule: "phase-has-workshop", subject: "px", why: "already built", closedBy: "task X" },
  ]);
  assert.deepEqual(live, []);
  assert.equal(stale.length, 1, "the exception no longer describes anything real");
});
