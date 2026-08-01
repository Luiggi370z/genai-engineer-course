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

export interface Workshop {
  id: string;
  title: string;
  subtitle: string;
  repo: string;
  /** Objectives the workshop puts together. A capstone should cover most of the phase. */
  assesses: ObjectiveRef[];
  needs?: ObjectiveRef[];
  blocks: Block[];
  deliverables: Checkable[];
  stretch?: string[];
}

export interface QuestionAnswer {
  id: string;
  q: string;
  a: string;
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
  checkpoint?: QuestionAnswer[];
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
