/**
 * The manifest's only real job is refusing to call a wall of ticks an achievement.
 *
 * So that is what these test: the standing rule, the one field worth forging, and
 * the shape of the page when there is no evidence at all. Imports the TypeScript
 * directly — Node strips the types.
 */
import assert from "node:assert/strict";
import { test } from "node:test";
import {
  buildCompletion,
  parseEvidence,
  renderCompletion,
  standingOf,
} from "../src/lib/manifest.ts";

const phase = (id, num, extra = {}) => ({
  id,
  num,
  title: `Phase ${num}`,
  objectives: [{ id: `${id}-o1`, text: "o" }],
  exercises: [{ id: `${id}-e1`, title: "e" }],
  ...extra,
});

const evidence = (over = {}) => ({
  generated_on: "2026-08-01",
  dimensions: { quality: { proven: 1, total: 2, complete: false } },
  claims: {
    "p2-retrieval": { dimension: "quality", phase: "2", status: "unproven", command: "make check" },
    "capstone-quality": {
      dimension: "quality",
      phase: "8",
      status: "proven",
      command: "make report",
    },
  },
  proven: 1,
  total: 2,
  complete: false,
  ...over,
});

const allProven = () =>
  evidence({
    claims: {
      a: { dimension: "quality", phase: "8", status: "proven", command: "make report" },
    },
  });

test("every box ticked with no evidence file is still self-reported", () => {
  // The rule the whole module exists for. If clicking could produce anything
  // better than this, the manifest would be a certificate you issue yourself.
  const phases = [phase("p1", 1)];
  const progress = { "p1-o1": true, "p1-e1": true };
  const built = buildCompletion(phases, progress, null, new Date("2026-08-01"));
  assert.equal(built.ticked, built.total);
  assert.equal(built.standing, "self-reported");
});

test("evidence with nothing proven does not lift the standing either", () => {
  const empty = evidence({
    claims: { a: { dimension: "quality", phase: "1", status: "unproven", command: "make check" } },
  });
  assert.equal(standingOf(10, 10, parseEvidence(JSON.stringify(empty))), "self-reported");
});

test("partial evidence reads as partly-evidenced, not as a percentage", () => {
  assert.equal(standingOf(10, 10, parseEvidence(JSON.stringify(evidence()))), "partly-evidenced");
});

test("evidence-backed needs the boxes AND every claim", () => {
  const proven = parseEvidence(JSON.stringify(allProven()));
  assert.equal(standingOf(10, 10, proven), "evidence-backed");
  assert.equal(standingOf(9, 10, proven), "partly-evidenced");
});

test("`complete` is recomputed from the rows, not read off the summary", () => {
  // The one field worth forging, and the rows that contradict it are right there.
  const lying = evidence({ complete: true, proven: 99 });
  const parsed = parseEvidence(JSON.stringify(lying));
  assert.equal(parsed.complete, false);
  assert.equal(parsed.proven, 1);
});

test("garbage and unrelated JSON return null rather than throwing", () => {
  assert.equal(parseEvidence("{not json"), null);
  assert.equal(parseEvidence('{"hello":"world"}'), null);
  assert.equal(parseEvidence("[1,2,3]"), null);
});

test("a manifest with no evidence says so, and says what to run", () => {
  const built = buildCompletion([phase("p1", 1)], {}, null, new Date("2026-08-01"));
  const page = renderCompletion(built);
  assert.match(page, /None attached/);
  assert.match(page, /make evidence/);
  assert.match(page, /not the same thing/);
});

test("unproven claims are printed with their commands, never omitted", () => {
  const built = buildCompletion(
    [phase("p1", 1)],
    {},
    parseEvidence(JSON.stringify(evidence())),
    new Date("2026-08-01"),
  );
  const page = renderCompletion(built);
  assert.match(page, /p2-retrieval/);
  assert.match(page, /make check/);
});

test("per-phase progress counts every checkable id in the phase", () => {
  const rich = phase("p1", 1, {
    checkpoint: [{ id: "p1-q1", q: "q", a: "a", demands: ["evidence", "constraints"] }],
    workshop: { deliverables: [{ id: "p1-d1", text: "d", tier: "minimum" }] },
    recall: [{ id: "p1-r1", q: "q", a: "a", from: "p0-o1" }],
    qbank: [{ group: "g", items: [{ id: "qb-1", q: "q", a: "a" }] }],
  });
  const built = buildCompletion([rich], { "p1-o1": true }, null, new Date("2026-08-01"));
  // objective, recall, exercise, deliverable, checkpoint, q-bank item.
  assert.equal(built.total, 6);
  assert.equal(built.ticked, 1);
});
