/**
 * The data-integrity rules, as a pure function over course data.
 *
 * The third of three gates, and the one that asks the dullest question: is this
 * data well-formed? Alignment asks whether a phase teaches what it tests, density
 * asks whether a human can get through a card. Neither notices a table with a
 * ragged row, a resource pointing at a typo, or two checkboxes sharing a progress
 * key — all of which type-check perfectly and all of which a student meets before
 * anyone else does.
 *
 * Kept pure so `integrity.test.mjs` can feed it broken data and prove each rule
 * fires. A gate nobody has seen fail is not a gate.
 */

import { KNOWN_KINDS } from "./density.mjs";

/**
 * Ids that are deliberately not phase-prefixed, and why.
 *
 * Workshop ids carry two historical schemes — `w1`–`w4` from the original course
 * order and `w-bench` / `w-evals` / `w-memory` / `w-deploy` / `w-interview` from
 * the phases inserted later — and renaming them would silently reset the progress
 * of anyone mid-course, since the id *is* the localStorage key. The q-bank is
 * global (`qb-1`…`qb-20`) because it is one interview deck rather than a phase's
 * property. Both are exempt on purpose rather than by oversight.
 */
const PREFIX_EXEMPT = new Set(["workshop", "deliverable", "qbank"]);

/**
 * @param {object} input
 * @param {any[]} input.phases         course data, in order
 * @param {any[]} [input.prerequisites]
 * @param {any[]} [input.electives]
 * @param {(repo: string) => boolean} [input.repoExists]
 * @returns {{ errors: {rule: string, subject: string, message: string}[], counts: object }}
 */
export function audit({ phases, prerequisites = [], electives = [], repoExists = () => true }) {
  const errors = [];
  const fail = (rule, subject, message) => errors.push({ rule, subject, message });

  checkIds(fail, { phases, prerequisites, electives });

  let blocks = 0;
  const visit = (block, subject) => {
    blocks += 1;
    checkBlock(block, subject, fail);
  };

  for (const phase of phases) {
    for (const concept of phase.concepts ?? []) walkBlocks(concept.blocks, concept.id, visit);
    if (phase.workshop) walkBlocks(phase.workshop.blocks, phase.workshop.id, visit);

    for (const resource of phase.resources ?? []) checkResource(resource, phase.id, fail);

    for (const objective of phase.objectives ?? []) {
      if (!text(objective.text)) fail("empty-content", objective.id, "objective has no text");
    }
    for (const concept of phase.concepts ?? []) {
      if (!text(concept.title)) fail("empty-content", concept.id, "concept card has no title");
      if (!(concept.blocks ?? []).length)
        fail("empty-content", concept.id, "concept card is empty");
    }
    for (const exercise of phase.exercises ?? []) {
      // Solution notes are the rubric on an independent task and the reasoning
      // behind the TODOs on a faded one. Either way an exercise without them
      // leaves the student no way to know whether they are done.
      if (!(exercise.solution ?? []).length) {
        fail("empty-content", exercise.id, "exercise ships no solution notes or rubric");
      }
    }
    if (phase.workshop && !(phase.workshop.deliverables ?? []).length) {
      fail("empty-content", phase.workshop.id, "workshop asks for no deliverables");
    }

    for (const { item, what } of tasksOf(phase)) {
      if (item.repo && !repoExists(item.repo)) {
        fail("repo-exists", item.id, `${what} points at src/${item.repo}, which does not exist`);
      }
    }
  }

  for (const elective of electives) {
    walkBlocks(elective.blocks, elective.id, visit);
    for (const resource of elective.resources ?? []) checkResource(resource, elective.id, fail);
    // The trigger is the only thing separating an elective from scope creep with a
    // nice heading, which is why the type demands one — but `""` satisfies a type.
    if (!text(elective.trigger)) {
      fail(
        "empty-content",
        elective.id,
        "elective states no trigger — the signal that makes it worth doing",
      );
    }
    if (!text(elective.cost)) fail("empty-content", elective.id, "elective states no time cost");
  }

  return {
    errors,
    counts: {
      ids: countIds({ phases, prerequisites, electives }),
      blocks,
      resources:
        phases.reduce((n, p) => n + (p.resources ?? []).length, 0) +
        electives.reduce((n, e) => n + (e.resources ?? []).length, 0),
      electives: electives.length,
    },
  };
}

/**
 * Every id, checked for collisions and for living under the right phase.
 *
 * Ids are localStorage progress keys, so a duplicate throws nowhere — it silently
 * ties two unrelated checkboxes together, and the student discovers it by ticking
 * one thing and watching another light up. This walk covers the q-bank,
 * prerequisites and electives, which the alignment gate never saw because it only
 * ever walked the phase spine it needed for the teaches/assesses graph.
 */
function checkIds(fail, { phases, prerequisites, electives }) {
  const seen = new Map();
  const claim = (id, where, phase = null, kind = null) => {
    if (!text(id)) {
      fail("empty-content", where, "carries no id, so its progress cannot be stored");
      return;
    }
    if (seen.has(id)) fail("id-unique", id, `duplicate id, also used by ${seen.get(id)}`);
    else seen.set(id, where);

    // A card copied from one phase file into another keeps its old prefix, and
    // nothing else notices unless its `teaches` happens to break too.
    if (phase && kind && !PREFIX_EXEMPT.has(kind) && !id.startsWith(`${phase.id}-`)) {
      fail(
        "id-prefix",
        id,
        `${kind} lives in ${phase.id} but its id is not prefixed "${phase.id}-"`,
      );
    }
  };

  for (const p of prerequisites) claim(p.id, "prerequisite");
  for (const e of electives) claim(e.id, "elective");

  for (const phase of phases) {
    const where = `phase ${phase.num}`;
    claim(phase.id, where);
    for (const o of phase.objectives ?? [])
      claim(o.id, `${phase.id} objective`, phase, "objective");
    for (const c of phase.concepts ?? []) claim(c.id, `${phase.id} concept`, phase, "concept");
    for (const e of phase.exercises ?? []) claim(e.id, `${phase.id} exercise`, phase, "exercise");
    for (const r of phase.recall ?? []) claim(r.id, `${phase.id} recall`, phase, "recall");
    for (const q of phase.checkpoint ?? [])
      claim(q.id, `${phase.id} checkpoint`, phase, "checkpoint");
    for (const group of phase.qbank ?? []) {
      for (const q of group.items ?? []) claim(q.id, `${phase.id} q-bank`, phase, "qbank");
    }
    if (phase.workshop) {
      claim(phase.workshop.id, `${phase.id} workshop`, phase, "workshop");
      for (const d of phase.workshop.deliverables ?? []) {
        claim(d.id, `${phase.workshop.id} deliverable`, phase, "deliverable");
      }
    }
  }
}

function countIds({ phases, prerequisites, electives }) {
  let n = prerequisites.length + electives.length;
  for (const phase of phases) {
    n +=
      1 +
      (phase.objectives ?? []).length +
      (phase.concepts ?? []).length +
      (phase.exercises ?? []).length +
      (phase.recall ?? []).length +
      (phase.checkpoint ?? []).length +
      (phase.qbank ?? []).reduce((m, g) => m + (g.items ?? []).length, 0) +
      (phase.workshop ? 1 + (phase.workshop.deliverables ?? []).length : 0);
  }
  return n;
}

const tasksOf = (phase) => [
  ...(phase.exercises ?? []).map((item) => ({ item, what: "exercise" })),
  ...(phase.workshop ? [{ item: phase.workshop, what: "workshop" }] : []),
];

/** Recurses, so a block inside a deep dive is held to the same rules as one outside. */
function walkBlocks(blocks, subject, visit) {
  for (const block of blocks ?? []) {
    visit(block, subject);
    if (block.kind === "deepdive") walkBlocks(block.blocks, subject, visit);
  }
}

function checkBlock(block, subject, fail) {
  if (!KNOWN_KINDS.has(block.kind)) {
    fail(
      "block-kind-known",
      subject,
      `block kind "${block.kind}" is not handled by the density walk in lib/density.mjs — ` +
        "it would render but escape the budget entirely",
    );
    return;
  }

  switch (block.kind) {
    case "p":
      if (!text(block.text)) fail("empty-content", subject, "an empty paragraph");
      break;
    case "list":
      if (!block.items.length) fail("empty-content", subject, "a list with no items");
      if (block.items.some((item) => !text(item))) {
        fail("empty-content", subject, "a list with a blank item");
      }
      break;
    case "code":
      if (!text(block.code)) fail("empty-content", subject, "a code block with no code");
      break;
    case "callout":
      if (!text(block.title) || !text(block.text)) {
        fail("empty-content", subject, `callout "${block.title}" is missing its title or body`);
      }
      break;
    case "table":
      checkTable(block, subject, fail);
      break;
    case "flow":
      if (!block.nodes.length) fail("empty-content", subject, "a flow with no nodes");
      if (block.nodes.some((node) => !text(node.label))) {
        fail("empty-content", subject, "a flow node with no label");
      }
      break;
    case "deepdive":
      if (!text(block.title)) fail("empty-content", subject, "a deep dive with no title");
      if (!(block.blocks ?? []).length) {
        fail("empty-content", subject, `deep dive "${block.title}" is empty`);
      }
      break;
    case "predict":
      // The consolidation is the half of the technique that does the teaching;
      // a blank one is a student being wrong and moving on.
      for (const field of ["prompt", "answer", "consolidation"]) {
        if (!text(block[field])) {
          fail("empty-content", subject, `a predict block with no ${field}`);
        }
      }
      break;
  }
}

/**
 * A ragged table does not throw and does not look broken in the source — the
 * renderer just drops the overflow or leaves a hole, and the column the author
 * meant to add is quietly absent from the page.
 */
function checkTable(block, subject, fail) {
  if (!block.headers.length || !block.rows.length) {
    fail("empty-content", subject, "a table with no headers or no rows");
    return;
  }
  block.rows.forEach((row, i) => {
    if (row.length !== block.headers.length) {
      fail(
        "table-shape",
        subject,
        `table row ${i + 1} has ${row.length} cell(s) against ${block.headers.length} header(s): "${row[0] ?? ""}"`,
      );
    }
  });
}

/**
 * Liveness is not checked — the build is offline and a gate that fails on someone
 * else's downtime is a gate people learn to skip. This catches the errors that are
 * ours: a relative path, a missing scheme, a label with no link behind it.
 */
function checkResource(resource, subject, fail) {
  if (!text(resource.label)) fail("empty-content", subject, "a resource with no label");
  let url;
  try {
    url = new URL(resource.url);
  } catch {
    fail("resource-url", subject, `"${resource.label}" has an unparseable url: ${resource.url}`);
    return;
  }
  if (url.protocol !== "http:" && url.protocol !== "https:") {
    fail(
      "resource-url",
      subject,
      `"${resource.label}" uses ${url.protocol}, which a browser will not follow`,
    );
  }
}

const text = (value) => typeof value === "string" && value.trim().length > 0;
