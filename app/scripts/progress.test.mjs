/**
 * Progress is the one piece of state the workbook keeps for a student across
 * eighteen weeks, so the rules worth testing are the ones that decide what they
 * are told about it and whether it survives a closed tab.
 *
 * Imports the TypeScript directly — Node strips the types.
 */
import assert from "node:assert/strict";
import { test } from "node:test";
import { formatPct, loadPlace, parseProgressFile, savePlace, tally } from "../src/lib/progress.ts";

/** A localStorage that behaves, since Node has none. */
function stubStorage() {
  const store = new Map();
  globalThis.localStorage = {
    getItem: (key) => store.get(key) ?? null,
    setItem: (key, value) => store.set(key, String(value)),
    removeItem: (key) => store.delete(key),
  };
  return store;
}

test("the first ticked box does not round away to nothing", () => {
  // 1 of 252 is 0.4%, which `Math.round` reported as 0% — the shipped bug.
  assert.equal(formatPct(1 / 252), "<1%");
  assert.equal(formatPct(0), "0%");
});

test("nearly finished is not finished", () => {
  assert.equal(formatPct(251 / 252), ">99%");
  assert.equal(formatPct(1), "100%");
});

test("the ordinary middle is an ordinary percentage", () => {
  assert.equal(formatPct(0.5), "50%");
  assert.equal(formatPct(0.126), "13%");
});

test("the count behind the ring is the count of ticked ids", () => {
  assert.deepEqual(tally({ a: true, b: false, c: true }, ["a", "b", "c", "d"]), {
    done: 2,
    total: 4,
  });
});

test("a place survives a round trip", () => {
  stubStorage();
  savePlace({ view: "p3", sectionId: "workshop" });
  assert.deepEqual(loadPlace(), { view: "p3", sectionId: "workshop" });
});

test("a place with no section is still a place", () => {
  stubStorage();
  savePlace({ view: "p3" });
  assert.deepEqual(loadPlace(), { view: "p3" });
});

test("garbage in storage reads as no place rather than throwing", () => {
  const store = stubStorage();
  store.set("genai_workbook_place_v1", "{not json");
  assert.equal(loadPlace(), null);
  store.set("genai_workbook_place_v1", JSON.stringify({ sectionId: "workshop" }));
  assert.equal(loadPlace(), null, "a section with no view points nowhere");
});

test("no storage at all is not an error — progress is a convenience", () => {
  globalThis.localStorage = undefined;
  assert.equal(loadPlace(), null);
  assert.doesNotThrow(() => savePlace({ view: "p1" }));
});

test("an imported progress file keeps only the booleans", () => {
  const parsed = parseProgressFile(
    JSON.stringify({ version: 1, progress: { "p1-o1": true, "p1-o2": "yes", "p1-o3": false } }),
  );
  assert.deepEqual(parsed, { "p1-o1": true, "p1-o3": false });
});
