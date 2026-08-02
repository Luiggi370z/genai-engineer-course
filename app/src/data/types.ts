/**
 * Content model for the workbook.
 *
 * Every renderable block kind must have a matching renderer in
 * `components/blocks/BlockList.tsx` — adding a kind here without one makes the
 * block silently disappear, so the two files change together.
 */

export type Block =
  | { kind: "p"; text: string }
  | { kind: "list"; items: string[] }
  | { kind: "code"; title?: string; code: string }
  | { kind: "callout"; tone: CalloutTone; title: string; text: string }
  | { kind: "table"; headers: string[]; rows: string[][] }
  /**
   * Where the numbers immediately above came from, and when someone last looked.
   *
   * Its own block kind rather than a field on `table`, because the claims that
   * rot fastest are not always in tables — a sentence about how many MCP servers
   * exist is exactly as perishable as a price row. Placing it after the block it
   * backs keeps the citation next to the claim, which is the only place a reader
   * will accept one.
   *
   * `verifiedOn` is the date, not a promise of freshness. A reader who can see
   * that a price was checked eleven months ago can discount it; a reader looking
   * at an undated number cannot, and will quote it.
   */
  | { kind: "sources"; verifiedOn: string; items: { label: string; url: string }[] }
  | { kind: "flow"; title?: string; shape?: FlowShape; nodes: FlowNode[] }
  | {
      kind: "deepdive";
      title: string;
      /**
       * Nested, which is what makes this the disclosure primitive rather than a
       * second kind of callout: anything that can appear on a card can appear
       * inside one, including a table or a code block.
       *
       * Its contents are excluded from the card's visible density budget — that
       * is the entire point — so the checker caps what can hide in here and
       * allows only one per card. Otherwise "collapse it" becomes a way to keep
       * writing rather than a reason to cut.
       */
      blocks: Block[];
    }
  | {
      kind: "predict";
      prompt: string;
      answer: string;
      /**
       * Required, and the whole reason this block kind is safe to use.
       * Problem-solving-before-instruction produces its effect only when the
       * attempt is followed by real teaching — a failure phase with no
       * consolidation is just a student being wrong and moving on. Making the
       * field non-optional means you cannot ship half the technique.
       */
      consolidation: string;
    };

export type CalloutTone = "tip" | "warn" | "fix";

/**
 * What the arrows in a flow block actually mean.
 *
 * `linear` is the default and the honest shape for a pipeline: A feeds B feeds C.
 * The other two exist because drawing them as a line was not a cosmetic
 * shortcoming, it was wrong — a calibration *loop* that dead-ends after five
 * steps, or five independent "first match wins" conditions that read as a
 * progression from the first option to the last.
 *
 * Positions are computed by the renderer, never authored. Hand-placed
 * coordinates in a data file go stale the first time a label gets longer.
 */
export type FlowShape = "linear" | "cycle" | "decision";

export interface FlowNode {
  label: string;
  sub?: string;
}

/** Anything the student can tick off; the id is the progress-store key. */
export interface Checkable {
  id: string;
  text: string;
}

export type Prerequisite = Checkable;

export interface Myth {
  title: string;
  text: string;
}

export interface Milestone {
  stage: string;
  bar: string;
}

/**
 * One thing the course deliberately does not teach, and where to go for it.
 * Stated up front because an unstated scope reads as a claim: a reader who
 * finishes nine phases without ever meeting backpropagation should have known
 * that on day one, not inferred it from an absence.
 */
export interface OutOfScope {
  topic: string;
  why: string;
  next: string;
}

/**
 * Objective ids, the join that makes constructive alignment checkable.
 *
 * A phase's objectives are the spine: concepts `teaches` them, exercises and
 * workshops `assesses` them. `scripts/check-alignment.mjs` walks those two
 * fields and fails the build when an exercise tests something no card taught —
 * the "taught 1+1, tested 1×1" gap. Both fields are **required** so a new,
 * unannotated card or exercise cannot compile.
 */
export type ObjectiveRef = string;

export interface Concept {
  id: string;
  title: string;
  tag?: string;
  /** Objectives this card develops. At least one — a card teaching nothing is a cut. */
  teaches: ObjectiveRef[];
  blocks: Block[];
}

export interface Example {
  title: string;
  text: string;
}

/**
 * Which rung of the worked → faded → independent ladder a task sits on.
 *
 * There is deliberately no `"worked"` value: the worked rung is the `after/`
 * reference and the concept card's code blocks — something the student *reads*,
 * not something they are set. Naming it here would invite an exercise that hands
 * over the answer and calls itself practice.
 *
 * Faded means a `before/` scaffold with the judgement removed. Independent means
 * a blank editor: no repo, no scaffold, no reference implementation. The order
 * matters more than the labels — an independent task before the fading has
 * happened is just an unfair one.
 */
export type Rung = "faded" | "independent";

/**
 * How far up the mastery ladder a task actually carries you.
 *
 * `Rung` says how much scaffolding a task removes. This says something
 * different and easier to get wrong: what the finished work *demonstrates*. A
 * blank-editor exercise can still only prove you can build a thing in isolation,
 * and a heavily-scaffolded workshop can prove you kept a system running under
 * load. The two axes are independent, and conflating them is how a syllabus ends
 * up promising "operate" and assessing "implement".
 *
 * - `understand` — you can explain it and answer a question about it. Proven by
 *   a checkpoint or a written argument, not by a repo. A task at this level is
 *   rare here on purpose: reading is not the product.
 * - `implement` — you built the thing, in isolation, and its tests are green.
 *   One lesson directory, no other moving parts.
 * - `integrate` — you made it work *with the rest of the system*, across a seam
 *   you do not fully control. The failures at this level are the ones that do
 *   not reproduce in a unit test.
 * - `operate` — you ran it under adverse conditions and have numbers: deployed,
 *   gated, traced, attacked, budgeted, or recovered. This is the only level that
 *   produces evidence somebody else would accept.
 *
 * The alignment gate reads this. An objective whose Bloom verb demands
 * `operate` and whose only assessment proves `implement` is the mismatch it
 * exists to catch — the course promising a level it never tests.
 */
export type Mastery = "understand" | "implement" | "integrate" | "operate";

export interface Exercise {
  id: string;
  title: string;
  task: string;
  repo?: string;
  /**
   * Required so an unlabelled exercise cannot compile, the same guardrail
   * `teaches` and `assesses` provide. An `"independent"` exercise must carry no
   * `repo` and no `code` — the checker enforces both, since either one would
   * hand back the scaffold the blank editor exists to remove.
   */
  rung: Rung;
  /**
   * What finishing this actually demonstrates. Required, so a new exercise
   * cannot quietly inherit a level it does not earn, and read by the alignment
   * gate against the Bloom verb of every objective it assesses.
   */
  proves: Mastery;
  /** Objectives this exercise tests. Each must be taught by a card in the same phase. */
  assesses: ObjectiveRef[];
  /**
   * Objectives from *earlier* phases this exercise leans on. The checker rejects
   * a forward reference, which is how "requires an untaught skill" gets caught
   * across phase boundaries rather than only inside one.
   */
  needs?: ObjectiveRef[];
  /**
   * For a faded exercise these are solution notes — the reasoning behind the
   * scaffold's TODOs. For an independent one they are a **rubric**: what a good
   * answer proves, stated so the student can grade themselves without ever being
   * shown an implementation to copy.
   */
  solution: string[];
  /** Reference implementation, revealed with the solution notes. Faded rung only. */
  code?: string;
}

/**
 * Which pass of the workshop a deliverable belongs to.
 *
 * `minimum` is the walking skeleton — the smallest set that makes the thing real
 * end to end. `full` is the version you would show someone. `stretch` is the
 * third tier and lives in its own field, because those are prompts rather than
 * checkboxes and giving them progress ids would let a workshop read 60% done
 * when it is finished.
 *
 * The split exists because an undifferentiated list of twenty-three deliverables
 * reads as one indivisible obligation, and the student who cannot fit all of it
 * this week does none of it. A named minimum is a place to stop that is not
 * quitting.
 */
export type DeliverableTier = "minimum" | "full";

export interface Deliverable extends Checkable {
  tier: DeliverableTier;
}

export interface Workshop {
  id: string;
  title: string;
  subtitle: string;
  repo: string;
  /** What finishing the workshop demonstrates. See `Mastery`. */
  proves: Mastery;
  /** Objectives the workshop puts together. A capstone should cover most of the phase. */
  assesses: ObjectiveRef[];
  needs?: ObjectiveRef[];
  blocks: Block[];
  deliverables: Deliverable[];
  stretch?: string[];
}

export interface QuestionAnswer {
  id: string;
  q: string;
  a: string;
}

/**
 * The four things a design answer has to contain before it counts as a defense.
 *
 * They are the difference between describing a system and defending one. A
 * description says what you built; a defense says what else you could have built
 * (`alternatives`), what ruled the others out (`constraints`), what makes you
 * believe the choice worked (`evidence`), and where it breaks (`failure-modes`).
 * Interviewers probe in roughly that order, and the last one is where most
 * candidates stop — which is exactly why it is a named element here rather than
 * a hoped-for bonus.
 */
export type DefenseElement = "alternatives" | "constraints" | "evidence" | "failure-modes";

/**
 * A spoken checkpoint, with the rubric its answer has to satisfy.
 *
 * `demands` is shown **before** the answer opens, because a bar you discover
 * afterwards is a bar you grade yourself against, and everyone passes that one.
 *
 * Two or more elements per question, not four. Four on every question would make
 * the rubric noise — "name the alternatives" does not apply to every prompt, and
 * a rubric that always says the same thing stops being read by the third card.
 * The coverage requirement lives one level up instead: the checker asserts every
 * phase's checkpoint set exercises all four across its questions, so no phase can
 * let you off the failure-modes hook.
 */
export interface Defense extends QuestionAnswer {
  demands: DefenseElement[];
}

export interface QuestionGroup {
  group: string;
  items: QuestionAnswer[];
}

/**
 * A retrieval-practice question drawn from an **earlier** phase.
 *
 * Two pieces of evidence shape this type. Retrieval beats re-reading, so the
 * question has to be answered rather than reviewed — which is why it renders as a
 * closed card, exactly like the checkpoint. And *interleaving* beats blocking, so
 * a set has to mix its sources: three questions all pulled from the phase you just
 * finished is massed practice wearing a recall badge, and the checker rejects it.
 *
 * These live at the top of a phase, not the bottom, because the point is to
 * reactivate the prior knowledge the new material is about to build on.
 */
export interface RecallCheck {
  id: string;
  q: string;
  a: string;
  /**
   * The earlier-phase objective this reaches back to. Enforced to resolve, and
   * enforced to be strictly earlier — a "recall" check pointing forward is asking
   * the student to remember something they have not met.
   */
  from: ObjectiveRef;
}

export interface Resource {
  label: string;
  url: string;
}

/** A phase as authored. `num` is assigned by the course order. */
export interface PhaseContent {
  id: string;
  weeks: string;
  color: string;
  title: string;
  tagline: string;
  /**
   * The sixty-second version of the phase, capped at 300 chars by the checker.
   *
   * Required rather than optional so a new phase cannot ship without one and
   * `tsc` says so immediately — the same guardrail as `teaches` and `rung`.
   * Reading time is not authored alongside it; it is derived from the phase's
   * visible prose, because a number typed by hand rots on the next edit.
   */
  tldr: string;
  /**
   * Each `text` must open with a bolded Bloom verb (`"**Implement** the four …"`).
   * The bold is not decoration: it puts the cognitive level in front of the
   * student, and it is what the alignment checker parses.
   */
  objectives: Checkable[];
  /**
   * Three interleaved questions from earlier phases, surfaced before the new
   * material. Absent on the first phase only — nothing precedes it.
   */
  recall?: RecallCheck[];
  concepts: Concept[];
  example?: Example;
  exercises: Exercise[];
  workshop?: Workshop;
  checkpoint?: Defense[];
  qbank?: QuestionGroup[];
  resources: Resource[];
}

export interface Phase extends PhaseContent {
  num: number;
}

/**
 * An optional side quest, deliberately outside the phase spine.
 *
 * Electives have **no objectives and no checkable ids**, which is the whole design.
 * The nine phases are a claim about what an entry-level GenAI engineer must be able
 * to do; an elective is a claim about what *some* roles additionally want. Giving
 * them progress ids would punish a student for skipping content they were correctly
 * told to skip, so `overallPct` ignores this file entirely and the alignment checker
 * — which only walks `phases` — never sees it.
 *
 * `trigger` is required for that reason: an elective that cannot state the concrete
 * signal that makes it worth your time is scope creep with a nice heading.
 */
export interface Elective {
  id: string;
  title: string;
  tag: string;
  /** The concrete signal that makes this worth doing. No trigger, no elective. */
  trigger: string;
  /** Roughly how long the first useful result takes, stated honestly. */
  cost: string;
  blocks: Block[];
  resources: Resource[];
}
