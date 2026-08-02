/**
 * Dashboard copy. Lived inline in the shipped bundle's components; pulled out
 * here so all editable content sits under `data/`.
 */

export const dashboard = {
  title: "The GenAI Engineer Workbook",
  refreshed: "refreshed August 2026",
  intro:
    'A friendly, fact-checked path from "I call LLM APIs sometimes" to "I ship evaluated, guarded, deployed GenAI systems" — the skill set hiring managers are actually screening for. ',
  introEmphasis: "Pace yourself by the gates, not the calendar.",
  progressCaption: "COMPLETE — your progress saves automatically",
  loop: [
    {
      step: "01",
      text: "Answer the three **recall** questions at the top of the phase before you read anything. They come from earlier phases, and getting one wrong is the point — that is how you find out what didn’t stick.",
    },
    {
      step: "02",
      text: "Read a concept card — each one is built to be read in under two minutes. Some open with a **predict-first** prompt: commit to an answer before you expand it, because a guess you own is what makes the explanation land.",
    },
    {
      step: "03",
      text: "Climb the **ladder**. Every phase runs *worked → faded → blank editor*: read the `after/` reference, fill in the `before/` scaffold, then build the last one from an empty directory with nothing to copy.",
    },
    {
      step: "04",
      text: "Ship it. Each lesson folder runs standalone: `make setup`, `make lint` (ruff), `make type` (pyright), `make test`.",
    },
    {
      step: "05",
      text: "Check it off here, answer the checkpoint out loud, and let the rings fill up.",
    },
  ],
  honestyNote:
    "Honesty corner: model names drift weekly — every price, tier and model tag on these pages carries the date it was last checked, printed under the table it belongs to; the durable bets are the patterns — provider-agnostic clients, hybrid retrieval + reranking, eval-first habits, layered guardrails. Benchmark on your own data, and treat any single salary number as directional.",
} as const;
