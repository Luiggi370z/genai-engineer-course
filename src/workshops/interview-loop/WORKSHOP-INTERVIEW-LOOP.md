# Workshop · The interview loop  (ends Phase 9)

Eight workshops in, you have a system: a bench, a retrieval service, an eval suite, an
agent with memory and guardrails, an MCP server, and a deployment with traces and a
cost ladder. You can also, right now, probably not explain it out loud for forty
minutes without losing the thread.

That gap is what this workshop closes. It is the only one with no code, and that is
deliberate — every deliverable here is a **habit with an artifact attached**, because
a habit with no artifact is a resolution and resolutions do not survive week three.

Two things get built. First, the **drill loop**: a schedule, a rubric you score
yourself against, and recordings that let you see what you actually said rather than
what you meant. Second, the **funnel**: four numbers that turn "the search isn't
working" into a specific stage with a specific fix.

## Why this is a workshop and not a checklist

Because it has a failure mode that a checklist hides. Ask any engineer six months out
of a course what happened to their learning plan, and the answer is almost always the
same shape: it was never scheduled, so it competed with everything else and lost.

The course was the forcing function. It is about to stop. What replaces it is the only
part of this workshop that matters after the offer lands, which is why `p7-o1` says
*design a durable learning system* and not *read about learning systems*. Skills in
AI-exposed roles churn roughly 66% faster than average — the system you build here is
the thing that stops that being your problem.

## Architecture

```
                        ┌── daily 20 min ──► 5 qbank questions, out loud, no notes
                        │                        └──► fumbled twice? ──► spaced list
your system ──► drills ─┤
 (workshops 1–8)        ├── 2×/week 45 min ─► recorded design mock
                        │                        └──► DESIGN-MOCK-RUBRIC.md ──► score
                        │
                        └── weekly 15 min ──► METRICS-WORKSHEET.md
                                                 ├─ part 1: numbers from your repos
                                                 └─ part 2: the funnel ──► one fix
                                                                             │
                             ┌───────────────────────────────────────────────┘
                             ▼
                    re-measure next week  (one variable at a time — like any eval)
```

The loop is the same one you have been running all course, pointed at yourself:
measure, find the failing stage, change one thing, re-measure. Phase 9's card calls
your search a funnel for exactly this reason.

## What you actually do

**The drill deck.** Twenty questions ship in Phase 9's bank. Five a day, out loud,
zero notes, self-graded against the reveal. Out loud is not a stylistic preference:
recognising a correct answer and producing one under pressure are different skills,
and interviews only test the second. Anything you fumble twice goes on a spaced list
and comes back in three days.

**The recorded mock.** Twice a week, one design prompt, timed, recorded, scored
against [`DESIGN-MOCK-RUBRIC.md`](DESIGN-MOCK-RUBRIC.md). Watching yourself is
unpleasant and it is the whole point — the rubric's rule is that anything you did not
say out loud scores zero, and only the recording can tell you which of those there
were. Expect the first score to be bad. A first mock that scores well usually means
you scored it generously.

**The metrics pass.** One afternoon, once, mining every number out of your eight
workshop READMEs into [`METRICS-WORKSHEET.md`](METRICS-WORKSHEET.md): faithfulness,
recall@k, P95 and P99, cost per request before and after the ladder, red-team pass
rate, tools shipped. They already exist. You generated them. This is copy-editing,
and it is the difference between "built a RAG chatbot" and a bullet an interviewer
asks a follow-up question about.

**The funnel.** Four ratios, updated weekly. Then the discipline: pick the **one**
leaking stage and apply **one** fix. Rewriting your resume, changing your targeting
and adding two projects in the same week teaches you nothing, because you will not
know which one moved the number — the same reason you change one variable at a time
in an eval.

## Deliverables

Three passes. **Minimum** is the walking skeleton — the smallest thing that is
really this, and a place to stop that is not quitting. **Full** is the version you
would show someone. **Stretch** is for when the full pass came easily.

### Minimum
- [ ] A **written weekly schedule** with the drill, mock and metrics slots on specific
      days at specific times, and a named trigger for each — the thing that already
      happens daily that the habit attaches to
- [ ] **Three recorded design mocks**, each scored on the rubric, with the scores
      trending — the trend is the deliverable, not the third score
- [ ] A **resume where every bullet carries a number**, and nothing survives without one

### Full
- [ ] A **spaced-repetition list** with real entries in it, proving you drilled long
      enough to fumble something twice
- [ ] Every rubric row scoring 0 or 1 has a **named drill** attached, so a weakness
      becomes a task rather than an observation
- [ ] A **metrics sheet** where every claim traces to a file, test or trace in one of
      your own repos, and any claim that cannot is deleted
- [ ] The **funnel, with at least 20 applications behind it**, your leaking stage
      named, and exactly one fix applied and dated
- [ ] A **learning system that outlives the course**: what you skim weekly, the
      personal eval set you keep growing, and what you build in public — plus the
      review date when you check whether you actually did any of it

## Stretch goals

- **Swap mocks with someone.** Self-scoring has a ceiling, and the ceiling is that
  you know what you meant. An outside scorer against the same rubric will find the
  step you think you covered and didn't.
- **Run the qbank against your own system.** For each of the twenty answers, point at
  the file in your repo that proves you have done it. Any answer with nothing behind
  it is a gap in the portfolio, not just in the drill.
- **Turn your personal eval set into the keep-up habit.** Keep `golden.jsonl` on a
  problem you actually care about. Every new model release becomes a ten-minute
  experiment instead of a vibes debate — and that is the honest answer to "how do you
  keep up", because it is a system rather than a claim about your reading habits.
- **Write the walkthrough.** One post, one diagram, one honest failure section — what
  you measured, what you got wrong, what you would do differently. It doubles as the
  forty-minute story and it means you have built in public at least once.

**The one number that decides this workshop worked.** Not how many questions you can
answer — whether you can take any single component of your system and defend the
decision behind it, with the measurement that drove it, without preparing first. That
is what the eight workshops were for. This one just makes it audible.
