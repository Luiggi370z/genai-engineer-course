/**
 * Where the nine workshop effort estimates come from.
 *
 * They used to come from a formula nobody had written down: every one of the nine had
 * `realistic` exactly 2x `fast`, and four shared one identical triple. Nine numbers
 * from five distinct guesses, presented to a learner planning a weekend as though
 * somebody had timed them.
 *
 * Nobody has timed them. There is no learner telemetry for this course, and inventing
 * some would be worse than the formula. So these are **author's estimates**, and the
 * word is chosen: a person set each one. What this module adds is that the person had
 * to answer to something. The repo contains four countable proxies for "how much work
 * is this", measured from source at check time, and an estimate has to sit inside the
 * range they span. Judgement picks the number; evidence bounds it.
 *
 * The alternative was tried first and abandoned on the evidence: deriving each figure
 * as the median of the proxies produced 15 minutes to build a retrieval core and 45 to
 * build an agent loop. The proxies disagree by 3-10x per workshop and they disagree
 * *directionally* — a workshop's scaffold deliberately stubs less than its brief asks
 * for, so the scaffold-based proxies read low exactly where the brief-based one reads
 * high. A median over contradictory evidence is not a derivation, it is a formula with
 * better manners, and it was the formula that started this.
 *
 * ## The proxies, and why there are four
 *
 * Each one is measurable and each one is wrong in a direction you can name:
 *
 * - `todoGroups` — numbered TODO stubs in the modules the brief names. Undercounts a
 *   workshop badly: `WORKSHOP-RAG-SERVICE.md` asks for hybrid search with an abstain
 *   path and the scaffold has three stubs, because a workshop asks you to design from
 *   a brief while a lesson asks you to fill in blanks.
 * - `suiteTests` — tests in the suites the brief names. Undercounts when a module's
 *   behaviour is proved in suites the brief does not name (`test_agent.py` has four
 *   tests; the agent is exercised across five other files).
 * - `deliverables` — Minimum and Full checkboxes in the brief. Granularity is the
 *   author's, not the work's: the deployed-stack brief carries sixty, several of
 *   which are one line of compose, so this proxy alone puts it at thirty hours.
 * - `briefWords` — reading the brief at 200 wpm. Small, and the only term here that
 *   is not really an estimate.
 *
 * A fifth was tried and dropped: net new lines between `before/` and `after/`. The
 * scaffolds are stubbed rather than absent, so it reports thirteen lines for a
 * workshop that builds a retrieval core, and a transitive import graph fails the
 * other way — `tools.py` is imported by almost everything downstream, which credits
 * that workshop with 162 tests it does not own.
 *
 * ## The rates are back-solved, not chosen
 *
 * `MIN_PER_TODO_GROUP` and `MIN_PER_TEST` are the medians implied by the course's own
 * 31 lesson estimates, which are the numbers that have actually been sat through. So
 * the workshops are calibrated against the lessons rather than against an opinion.
 * The lesson `realistic / fast` median is 1.67, which is why the ratios below cluster
 * near it and why none of them is 2.00 any more.
 *
 * ## What these numbers are not
 *
 * They are not learner-tested, and the workbook and every brief say so in those words.
 * The honest uncertainty is the spread between the proxies, which is wide. Read them
 * as "this workshop is roughly twice that one", which the proxies do agree on, and not
 * as "this takes 120 minutes".
 */

/**
 * The line every brief carries under its `**Effort.**` figure.
 *
 * Separate from the figure because `check-integrity` re-renders that line from the
 * workbook's data and demands an exact match, so the honesty cannot live inside it.
 * Identical in all nine so a learner comparing two workshops is reading one claim.
 */
export const PROVENANCE_NOTE =
  "*An author's estimate, bounded by measured volume — deliverables, TODO groups, " +
  "tests, brief length — and not by learner telemetry, which this course does not " +
  "collect. Treat it as relative sizing, not a stopwatch.*";

/** Median of the 31 lesson estimates: `fast` divided by numbered TODO groups. */
export const MIN_PER_TODO_GROUP = 5.7;

/** Median of the same 31: `fast` divided by tests in the lesson's own suite. */
export const MIN_PER_TEST = 4.4;

/**
 * Minutes per Minimum-or-Full deliverable. The one rate with no lesson to anchor it,
 * because lessons have no deliverables — it is the median lesson `fast` (45 min)
 * against the median lesson's TODO-group count, taken as a stand-in for "one
 * behaviour a reviewer could check". Held to a round number to avoid dressing a
 * judgement as a measurement.
 */
export const MIN_PER_DELIVERABLE = 30;

/** Reading speed for the brief, in words per minute. Conventional. */
export const WORDS_PER_MINUTE = 200;

/** Median `realistic / fast` across the 31 lesson estimates. */
export const REALISTIC_UPLIFT = 1.67;

/**
 * Which source belongs to which workshop, and what its integration tier costs.
 *
 * `modules` and `suites` are the paths the brief itself names under `Implement …` and
 * `Tests: …`, so this map is checkable against the briefs rather than invented here.
 *
 * `integrationMin` cannot be derived from source — it is wall-clock, and it is the
 * one number here that really was measured. `recorded` says on what.
 */
export const WORKSHOPS = {
  "w-bench": {
    repo: "workshops/model-bench",
    pkg: "bench",
    brief: "WORKSHOP-MODEL-BENCH.md",
    modules: null, // the brief says `after/src/bench/`, so: the package
    suites: null,
    integrationMin: 60,
    recorded: "hosted-provider round trips across three models, metered by the lesson itself",
  },
  w1: {
    repo: "workshops/assistant",
    pkg: "assistant",
    brief: "WORKSHOP-RAG-SERVICE.md",
    modules: ["rag"],
    // Both, because the brief names both. It used to name only `test_rag.py`, whose
    // two tests are the walking skeleton — grounding, abstention and citations are
    // proved in `test_retrieval.py`, and a learner sent to the wrong file thinks a
    // green skeleton is a finished workshop.
    suites: ["test_rag", "test_retrieval"],
    integrationMin: 60,
    recorded: "Qdrant + Ollama first boot and the embedding of the sample corpus",
  },
  "w-evals": {
    repo: "workshops/assistant",
    pkg: "assistant",
    brief: "WORKSHOP-EVAL-SUITE.md",
    modules: ["evals"],
    suites: ["test_evals"],
    integrationMin: 30,
    recorded: "one judged pass over the golden set on the local judge model",
  },
  w2: {
    repo: "workshops/assistant",
    pkg: "assistant",
    brief: "WORKSHOP-ASSISTANT.md",
    modules: ["tools", "agent"],
    suites: ["test_agent"],
    integrationMin: 30,
    recorded: "tool-calling round trips against a local model",
  },
  "w-memory": {
    repo: "workshops/assistant",
    pkg: "assistant",
    brief: "WORKSHOP-MEMORY-CREW.md",
    modules: ["memory", "tenancy", "crew"],
    suites: ["test_memory", "test_tenancy", "test_crew"],
    integrationMin: 30,
    recorded: "multi-turn recall against a running store",
  },
  w3: {
    repo: "workshops/assistant",
    pkg: "assistant",
    brief: "WORKSHOP-HARDENED.md",
    modules: ["guardrails", "screening", "guard"],
    suites: ["test_guardrails", "test_guard", "test_security"],
    integrationMin: 60,
    recorded: "the red-team dataset run against a model in the loop",
  },
  w4: {
    repo: "workshops/assistant",
    pkg: "assistant",
    brief: "WORKSHOP-MCP.md",
    modules: ["mcp_client", "planner"],
    suites: ["test_mcp", "test_planner"],
    integrationMin: 60,
    recorded: "a real MCP server over stdio, plus Inspector",
  },
  "w-deploy": {
    repo: "workshops/assistant",
    pkg: "assistant",
    brief: "WORKSHOP-DEPLOYED-STACK.md",
    modules: ["observe", "provenance", "usage", "core", "cache"],
    suites: ["test_observe", "test_tracing", "test_cache"],
    integrationMin: 120,
    recorded:
      "the e2e suite on the reference machine: 1097 s cold, 1498 s worst observed, " +
      "plus model pulls into a fresh volume",
  },
  "w-interview": {
    repo: "workshops/interview-loop",
    pkg: null, // markdown only: no scaffold, so two of the four proxies read zero
    brief: "WORKSHOP-INTERVIEW-LOOP.md",
    modules: [],
    suites: [],
    integrationMin: null,
    recorded: null,
  },
};

/** Numbered TODO groups, plus any bare `TODO`, in the modules a brief names. */
export function todoGroups(read, { repo, pkg, modules }) {
  if (!pkg) return 0;
  const names = modules?.length
    ? modules
    : read.list(`src/${repo}/before/src/${pkg}`).map((f) => f.replace(/\.py$/, ""));
  let total = 0;
  for (const name of names) {
    if (name === "__init__") continue;
    const body = read.file(`src/${repo}/before/src/${pkg}/${name}.py`);
    if (body === null) continue;
    const numbered = new Set([...body.matchAll(/TODO\s*(\d+)/g)].map((m) => m[1]));
    const bare = [...body.matchAll(/TODO(?!\s*\d)/g)].length;
    total += numbered.size + bare;
  }
  return total;
}

/** Tests in the suites a brief names. */
export function suiteTests(read, { repo, pkg, suites }) {
  if (!pkg) return 0;
  const names = suites?.length
    ? suites
    : read.list(`src/${repo}/after/tests`).map((f) => f.replace(/\.py$/, ""));
  let total = 0;
  for (const name of names) {
    if (!name.startsWith("test_")) continue;
    const body = read.file(`src/${repo}/after/tests/${name}.py`);
    if (body === null) continue;
    total += [...body.matchAll(/^\s*def test/gm)].length;
  }
  return total;
}

/**
 * Deliverables and length, from the brief.
 *
 * Stretch is excluded on purpose: the brief calls it "for when the full pass came
 * easily", so counting it would bill every learner for optional work.
 */
export function briefShape(read, { repo, brief }) {
  const body = read.file(`src/${repo}/${brief}`);
  if (body === null) return { deliverables: 0, words: 0 };
  let counting = false;
  let deliverables = 0;
  for (const line of body.split("\n")) {
    const heading = /^#+\s+(.+)/.exec(line);
    if (heading) {
      const name = heading[1].toLowerCase();
      // "Full — a model in the loop" is a Full tier; "Stretch" never counts.
      counting =
        !name.startsWith("stretch") &&
        (name.startsWith("minimum") ||
          name.startsWith("full") ||
          name.startsWith("deliverable") ||
          name.startsWith("capstone deliverable"));
    } else if (counting && line.startsWith("- [ ]")) {
      deliverables += 1;
    }
  }
  return { deliverables, words: body.split(/\s+/).filter(Boolean).length };
}

/** Every proxy for one workshop, in minutes of build time. */
export function proxies(read, workshop) {
  const groups = todoGroups(read, workshop);
  const tests = suiteTests(read, workshop);
  const { deliverables, words } = briefShape(read, workshop);
  return {
    counts: { groups, tests, deliverables, words },
    minutes: {
      todos: groups * MIN_PER_TODO_GROUP,
      tests: tests * MIN_PER_TEST,
      deliverables: deliverables * MIN_PER_DELIVERABLE,
    },
    readingMin: words / WORDS_PER_MINUTE,
  };
}

/** Nearest quarter hour, never zero — every estimate in the course is a multiple of 15. */
export function round15(minutes) {
  return Math.max(15, Math.round(minutes / 15) * 15);
}

/**
 * The estimates themselves, and the sentence that had to be true to write each one.
 *
 * Every `fast` here sits inside the envelope its proxies span — `envelope()` proves
 * it, so adding deliverables to a brief or gutting a suite can move the bound out from
 * under a number and fail the build. `why` is the judgement the bound cannot make:
 * which end of a wide range this workshop belongs at, and what the proxies miss.
 *
 * All multiples of 30, because `duration()` in `src/lib/effort.ts` renders anything
 * past two hours in hours and a half-hour is the coarsest unit that stays exact.
 */
export const ESTIMATES = {
  "w-bench": {
    fast: 150,
    realistic: 240,
    why: "Five small modules and a report, but the work is judgement rather than code — picking an axis, defending a ranking. The tests proxy (110) is the honest floor and deliverables (210) counts a rubric as if it were a module.",
  },
  w1: {
    fast: 120,
    realistic: 210,
    why: "Hybrid retrieval plus an abstain path, which is two hard behaviours in four deliverables. Sits at the top of the envelope because the three TODO stubs are the least representative count in the course: the brief asks you to design a retriever, not to fill in three blanks.",
  },
  "w-evals": {
    fast: 120,
    realistic: 180,
    why: "Two proxies agree closely here (74 and 75) and deliverables disagrees hard (210). Landed above the pair because writing a golden set is the slow part and no proxy can see it, and below deliverables because seven checkboxes over one module is a fine-grained brief.",
  },
  w2: {
    fast: 120,
    realistic: 180,
    why: "The widest disagreement of the nine (18 to 180) and the least useful evidence: `tools` and `agent` are imported by eleven suites, so no suite owns them and the named one has four tests. Priced as a lesson-and-a-half of loop plus two tools.",
  },
  "w-memory": {
    fast: 210,
    realistic: 330,
    why: "Three modules, ten deliverables, forty tests — the one workshop where every proxy agrees it is large (143, 176, 300). Raised from the old 180 because two proxies already sat above that figure.",
  },
  w3: {
    fast: 210,
    realistic: 360,
    why: "Twelve deliverables across three modules including a model-in-the-loop tier, and forty-two tests. The old 120 was the clearest underestimate in the set: two of three proxies sat above it and one sat at triple.",
  },
  w4: {
    fast: 120,
    realistic: 210,
    why: "A client and a planner against a real server. Modest code, but the Inspector loop and stdio transport are where the time actually goes, and that is integration time rather than build time.",
  },
  "w-deploy": {
    fast: 480,
    realistic: 900,
    why: "The capstone: sixty deliverables, a 4518-word brief, forty-four TODO groups. The old 300 priced deploying, observing, authenticating and rate-limiting a service at five hours. Raised to eight, still well under the deliverables proxy (1800), which counts one line of compose the same as a tracing seam.",
  },
  "w-interview": {
    fast: 180,
    realistic: 300,
    why: "Markdown only, so two proxies read zero and the envelope widens around the one that does not. Eight deliverables of mock interviews and written answers, which is an afternoon rather than the 240 a flat per-deliverable rate implies.",
  },
};

/**
 * The range the proxies span, which an estimate has to sit inside.
 *
 * Two or more live proxies bound each other and the envelope is simply their range.
 * One live proxy cannot be checked against anything, so it gets +/-50% — enough room
 * for a judgement, tight enough to catch an order of magnitude.
 */
export function envelope(read, workshop) {
  const { minutes, readingMin } = proxies(read, workshop);
  const live = Object.values(minutes).filter((m) => m > 0);
  if (!live.length) return null;
  const [low, high] =
    live.length > 1 ? [Math.min(...live), Math.max(...live)] : [live[0] * 0.5, live[0] * 1.5];
  return { low: low + readingMin, high: high + readingMin };
}

/** Everything known about one workshop's estimate: the counts, the bound, the number. */
export function assess(read, id, workshop) {
  const measured = proxies(read, workshop);
  const bound = envelope(read, workshop);
  const { fast, realistic, why } = ESTIMATES[id];
  return {
    ...measured,
    bound,
    why,
    fast,
    integration: workshop.integrationMin,
    realistic,
    inBound: bound ? fast >= Math.floor(bound.low) && fast <= Math.ceil(bound.high) : false,
  };
}
