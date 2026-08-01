// Generated from the shipped course bundle by scripts/extract-data.mjs.
// Edit freely from here on — this file is the source of truth for the content.

import type { Phase, PhaseContent } from "../types";
import { agents } from "./agents";
import { deploy } from "./deploy";
import { designDefend } from "./design-defend";
import { evals } from "./evals";
import { foundations } from "./foundations";
import { mcp } from "./mcp";
import { memory } from "./memory";
import { mindset } from "./mindset";
import { retrieval } from "./retrieval";

/** Course order. Phase numbers are derived from this list, never hard-coded. */
const ordered: PhaseContent[] = [
  foundations,
  retrieval,
  evals,
  agents,
  memory,
  designDefend,
  mcp,
  deploy,
  mindset,
];

export const phases: Phase[] = ordered.map((phase, i) => ({ ...phase, num: i + 1 }));
