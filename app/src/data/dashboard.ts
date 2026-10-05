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
  workshops: [
    {
      step: "01",
      text: "`src/phase1-foundations` through `src/phase9-mindset` are the short lessons. Each lesson has its own `before/` and `after/`.",
    },
    {
      step: "02",
      text: "`src/workshops/assistant/phases/02-rag` through `08-evidence` are the workshop for that phase. Work in `before/`. Diff against that folder's `after/`.",
    },
    {
      step: "03",
      text: "Open the folder this workshop page names. Edit only the files it names. Every other file in the folder is already finished, so this step can run.",
    },
    {
      step: "04",
      text: "From that `before/` folder, run `make setup` once, then `make test`. `make test` runs only that folder. The first failure is the one this page names.",
    },
    {
      step: "05",
      text: "A failure in a file this page does not name means you opened a different folder. Come back to the path on this page.",
    },
    {
      step: "06",
      text: "The next workshop is the next folder. You do not copy your code forward. The next `before/` already includes what you just finished.",
    },
    {
      step: "07",
      text: "`src/workshops/assistant/after` is the finished assistant Docker builds. The defect lab runs there, after the six Phase 8 folders.",
    },
    {
      step: "08",
      text: "`generator/` builds the phase folders. Leave it alone.",
    },
    {
      step: "09",
      text: "`ARCHITECTURE.md` is the map of one request. Open it when you need to see how the pieces connect.",
    },
    {
      step: "10",
      text: "`THREAT-MODEL.md` is which attack each file stops, and which test proves it. Open it when the workshop is about an attacker.",
    },
    {
      step: "11",
      text: "`RUNBOOK.md` is what you do after something breaks: start from the request id, then the trace, then the audit log. Open it in the deploy workshop, not while you are still writing `rag.py`.",
    },
    {
      step: "12",
      text: "`adr/` is the written decisions. Open one when you want the reason, not the steps.",
    },
    {
      step: "13",
      text: "Workshop 1 is its own project, `src/workshops/model-bench/before`. Workshop 9 has no code: a recorded mock, a metrics sheet, and one fix to the funnel.",
    },
  ],
  honestyNote:
    "Honesty corner: model names drift weekly — every price, tier and model tag on these pages carries the date it was last checked, printed under the table it belongs to; the durable bets are the patterns — provider-agnostic clients, hybrid retrieval + reranking, eval-first habits, layered guardrails. Benchmark on your own data, and treat any single salary number as directional.",
} as const;
