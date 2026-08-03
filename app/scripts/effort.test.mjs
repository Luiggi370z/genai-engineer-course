import assert from "node:assert/strict";
import { test } from "node:test";
import {
  assess,
  briefShape,
  ESTIMATES,
  envelope,
  PROVENANCE_NOTE,
  round15,
  suiteTests,
  todoGroups,
  WORKSHOPS,
} from "./lib/effort.mjs";

/** A stand-in repo, so these tests describe the rules rather than the course. */
function fakeRepo(files) {
  return {
    file: (path) => files[path] ?? null,
    list: (path) =>
      Object.keys(files)
        .filter((f) => f.startsWith(`${path}/`) && f.endsWith(".py"))
        .map((f) => f.slice(path.length + 1)),
  };
}

const WORKSHOP = {
  repo: "workshops/x",
  pkg: "x",
  brief: "BRIEF.md",
  modules: ["a"],
  suites: ["test_a"],
};

test("a numbered TODO counts once however many lines it spans", () => {
  const read = fakeRepo({
    "src/workshops/x/before/src/x/a.py": [
      "# TODO 1: the first thing",
      "#   TODO 1: still the first thing, continued",
      "# TODO 2: the second",
    ].join("\n"),
  });
  assert.equal(todoGroups(read, WORKSHOP), 2);
});

test("a bare TODO is its own group, since nothing else can tell them apart", () => {
  const read = fakeRepo({
    "src/workshops/x/before/src/x/a.py": "# TODO: one\n# TODO: two\n# TODO 1: numbered\n",
  });
  assert.equal(todoGroups(read, WORKSHOP), 3);
});

test("a markdown-only workshop has no scaffold and reads zero rather than throwing", () => {
  const read = fakeRepo({});
  assert.equal(todoGroups(read, { ...WORKSHOP, pkg: null }), 0);
  assert.equal(suiteTests(read, { ...WORKSHOP, pkg: null }), 0);
});

test("tests are counted in the suites the brief names, indented or not", () => {
  const read = fakeRepo({
    "src/workshops/x/after/tests/test_a.py":
      "def test_one():\n    pass\n\nclass TestGroup:\n    def test_two(self):\n        pass\n",
  });
  assert.equal(suiteTests(read, WORKSHOP), 2);
});

test("Stretch deliverables do not count, because the brief calls them optional", () => {
  const read = fakeRepo({
    "src/workshops/x/BRIEF.md": [
      "# Brief",
      "## Minimum",
      "- [ ] one",
      "## Full",
      "- [ ] two",
      "- [ ] three",
      "## Stretch",
      "- [ ] not billed",
      "- [ ] nor this",
    ].join("\n"),
  });
  assert.equal(briefShape(read, WORKSHOP).deliverables, 3);
});

test("'Full — a model in the loop' is a Full tier, not a section that stops counting", () => {
  const read = fakeRepo({
    "src/workshops/x/BRIEF.md": "## Full\n- [ ] a\n## Full — a model in the loop\n- [ ] b\n",
  });
  assert.equal(briefShape(read, WORKSHOP).deliverables, 2);
});

test("two live proxies bound each other; one gets room for a judgement", () => {
  const both = fakeRepo({
    "src/workshops/x/before/src/x/a.py": "# TODO 1: x\n", // 1 group  -> 5.7 min
    "src/workshops/x/after/tests/test_a.py": "def test_x():\n    pass\n", // 1 test -> 4.4 min
    "src/workshops/x/BRIEF.md": "## Minimum\n- [ ] one\n", // 1 deliverable -> 30 min
  });
  const wide = envelope(both, WORKSHOP);
  assert.equal(Math.round(wide.low), 4);
  assert.equal(Math.round(wide.high), 30);

  const lonely = fakeRepo({ "src/workshops/x/BRIEF.md": "## Minimum\n- [ ] one\n" });
  const narrow = envelope(lonely, WORKSHOP);
  assert.equal(Math.round(narrow.low), 15); // 30 * 0.5
  assert.equal(Math.round(narrow.high), 45); // 30 * 1.5
});

test("no proxy at all means nothing bounds the estimate, and that is reported not guessed", () => {
  assert.equal(envelope(fakeRepo({}), WORKSHOP), null);
});

test("estimates round to a quarter hour and never to nothing", () => {
  assert.equal(round15(7), 15);
  assert.equal(round15(0), 15);
  assert.equal(round15(112), 105);
  assert.equal(round15(113), 120);
});

test("every real workshop estimate sits inside the range its evidence spans", async () => {
  const { readFileSync, readdirSync } = await import("node:fs");
  const { dirname, resolve } = await import("node:path");
  const { fileURLToPath } = await import("node:url");
  const repo = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
  const read = {
    file(path) {
      try {
        return readFileSync(resolve(repo, path), "utf8");
      } catch {
        return null;
      }
    },
    list(path) {
      try {
        return readdirSync(resolve(repo, path)).filter((f) => f.endsWith(".py"));
      } catch {
        return [];
      }
    },
  };
  for (const [id, workshop] of Object.entries(WORKSHOPS)) {
    const found = assess(read, id, workshop);
    assert.ok(found.bound, `${id}: nothing bounds this estimate`);
    assert.ok(
      found.inBound,
      `${id}: ${found.fast} min is outside ${Math.round(found.bound.low)}-${Math.round(found.bound.high)}`,
    );
    assert.ok(found.why.length > 40, `${id}: the reasoning is too thin to review`);
  }
});

test("the ratios are not one number wearing nine hats", () => {
  const ratios = new Set(Object.values(ESTIMATES).map((e) => (e.realistic / e.fast).toFixed(2)));
  assert.ok(ratios.size >= 3, `only ${ratios.size} distinct ratio(s): ${[...ratios]}`);
  assert.ok(!ratios.has("2.00"), "2.00 is the formula this replaced");
});

test("the provenance line refuses the word the audit objected to", () => {
  assert.match(PROVENANCE_NOTE, /not by learner telemetry/);
  assert.doesNotMatch(PROVENANCE_NOTE, /learner-tested/);
});
