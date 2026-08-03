/**
 * The completion manifest — what you finished, and how much of it is provable.
 *
 * The workbook already knows what you ticked. Ticking is a claim, and a manifest
 * built only from claims is a certificate you issued to yourself: it reads the
 * same for someone who did the work and someone who clicked through, and so it
 * tells a reader nothing about either.
 *
 * So this takes a second input — `evidence/manifest.json`, written by
 * `make evidence` in the capstone, where every row is backed by a file some
 * phase actually produced. The two are reported side by side and never merged.
 * You can tick every box in the app and the manifest will still say
 * `self-reported`, because that is what it is.
 */
import type { Phase } from "../data/types";
// Extension included on purpose: `scripts/manifest.test.mjs` imports this file
// directly under bare Node, which strips types but does not resolve extensions.
import { type Progress, phaseIds } from "./progress.ts";

export interface EvidenceClaim {
  dimension: string;
  phase: string;
  status: "proven" | "unproven";
  command: string;
  measured_on: string | null;
  values: Record<string, unknown>;
}

export interface EvidenceManifest {
  generated_on: string;
  dimensions: Record<string, { proven: number; total: number; complete: boolean }>;
  claims: Record<string, EvidenceClaim>;
  proven: number;
  total: number;
  complete: boolean;
}

/**
 * How much of this manifest a stranger should believe.
 *
 * Three values rather than a percentage, because the distinction is categorical:
 * a claim is either backed by a file or it is not, and averaging the two would
 * let a wall of ticks dilute the absence of evidence into a respectable number.
 */
export type Standing = "self-reported" | "partly-evidenced" | "course-evidence-attached";

export interface PhaseCompletion {
  id: string;
  num: number;
  title: string;
  ticked: number;
  total: number;
}

export interface Completion {
  generatedOn: string;
  phases: PhaseCompletion[];
  ticked: number;
  total: number;
  evidence: EvidenceManifest | null;
  standing: Standing;
}

/** Never throws: a mistyped path or an unrelated JSON file is a normal event. */
export function parseEvidence(raw: string): EvidenceManifest | null {
  try {
    const parsed: unknown = JSON.parse(raw);
    if (typeof parsed !== "object" || parsed === null) return null;
    const box = parsed as Record<string, unknown>;
    if (typeof box.proven !== "number" || typeof box.total !== "number") return null;
    if (typeof box.claims !== "object" || box.claims === null) return null;
    if (typeof box.dimensions !== "object" || box.dimensions === null) return null;
    // `complete` is recomputed rather than read. It is the one field worth
    // forging, and the claim map is right there — trusting the summary over the
    // rows it summarises is how a manifest becomes a formality.
    const claims = box.claims as Record<string, EvidenceClaim>;
    const rows = Object.values(claims);
    return {
      generated_on: typeof box.generated_on === "string" ? box.generated_on : "",
      dimensions: box.dimensions as EvidenceManifest["dimensions"],
      claims,
      proven: rows.filter((c) => c.status === "proven").length,
      total: rows.length,
      complete: rows.length > 0 && rows.every((c) => c.status === "proven"),
    };
  } catch {
    return null;
  }
}

export function buildCompletion(
  phases: Phase[],
  progress: Progress,
  evidence: EvidenceManifest | null,
  now: Date = new Date(),
): Completion {
  const rows = phases.map((phase) => {
    const ids = phaseIds(phase);
    return {
      id: phase.id,
      num: phase.num,
      title: phase.title,
      ticked: ids.filter((id) => progress[id]).length,
      total: ids.length,
    };
  });
  const ticked = rows.reduce((n, p) => n + p.ticked, 0);
  const total = rows.reduce((n, p) => n + p.total, 0);
  return {
    generatedOn: now.toISOString().slice(0, 10),
    phases: rows,
    ticked,
    total,
    evidence,
    standing: standingOf(ticked, total, evidence),
  };
}

/**
 * No evidence file means `self-reported`, however many boxes are ticked. That is
 * the whole rule, and it is deliberately not gradeable by clicking.
 *
 * The top standing is `course-evidence-attached`, and the name is careful because
 * the earlier one — `evidence-backed` — claimed more than this function can check.
 * Two independent things are being combined here: every workbook item is ticked
 * (self-reported, one click each) and every claim in the capstone's evidence
 * manifest is proven (measured, by a command). What does NOT exist is a mapping
 * between the two. Nothing links item 137 to a particular claim, so "all boxes
 * ticked AND all claims proven" cannot mean "every box is proven" — the honest
 * reading is "this reader finished the workbook and the course's own evidence is
 * attached to it", which is what the name now says.
 *
 * Building the mapping would be the better fix and a much larger one: 252 items
 * against 13 claims, most of them learner work no command in this repo can
 * observe. Renaming was chosen over implying a link that is not there.
 */
export function standingOf(
  ticked: number,
  total: number,
  evidence: EvidenceManifest | null,
): Standing {
  if (!evidence || evidence.proven === 0) return "self-reported";
  if (evidence.complete && total > 0 && ticked === total) return "course-evidence-attached";
  return "partly-evidenced";
}

const STANDING_MEANS: Record<Standing, string> = {
  "self-reported":
    "Everything here is a claim I made about my own work. Nothing on this page is backed by an artifact.",
  "partly-evidenced":
    "Some claims are backed by files the course generated; the unproven ones are listed with the command that would close them.",
  "course-evidence-attached":
    "Every workbook item is ticked — those are my own claims about my own work — and every claim the COURSE makes about its reference implementation is backed by a file a reader can regenerate. The two are not linked: no individual item here is proven by an artifact.",
};

/** Markdown, for pasting into a repo README where a reader will actually find it. */
export function renderCompletion(completion: Completion): string {
  const lines: string[] = [
    "# Course completion manifest",
    "",
    `Generated ${completion.generatedOn} · **${completion.standing}** · ` +
      `${completion.ticked}/${completion.total} workbook items`,
    "",
    STANDING_MEANS[completion.standing],
    "",
    "| Phase | Progress |",
    "|---|---|",
  ];
  for (const phase of completion.phases) {
    lines.push(`| ${phase.num}. ${phase.title} | ${phase.ticked}/${phase.total} |`);
  }

  const evidence = completion.evidence;
  if (!evidence) {
    lines.push(
      "",
      "## Evidence",
      "",
      "None attached. Run `make evidence` in `workshops/assistant/after` and load the " +
        "`evidence/manifest.json` it writes — until then this page records what I say " +
        "I did, which is not the same thing and should not be read as if it were.",
    );
    return lines.join("\n");
  }

  lines.push(
    "",
    "## Evidence",
    "",
    `Generated ${evidence.generated_on} · **${evidence.proven}/${evidence.total} claims proven**`,
    "",
    "| Dimension | Proven |",
    "|---|---|",
  );
  for (const [dimension, count] of Object.entries(evidence.dimensions)) {
    lines.push(`| ${dimension} | ${count.proven}/${count.total} |`);
  }

  const open = Object.entries(evidence.claims).filter(([, c]) => c.status !== "proven");
  if (open.length) {
    lines.push("", "Still unproven, with the command that closes each:", "");
    for (const [id, claim] of open) lines.push(`- \`${id}\` — \`${claim.command}\``);
  }
  return lines.join("\n");
}
