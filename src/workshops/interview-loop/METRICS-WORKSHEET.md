# Metrics worksheet

Two parts. **Part 1** mines the numbers you already produced out of Workshops 1–8, once.
**Part 2** is the funnel, updated weekly forever after.

---

## Part 1 · Mine your own repos

Every row below exists somewhere in your work — in a test, a report file, a trace, a
`bench.json`. You generated all of it. This is an afternoon of copy-editing, not new
work.

**The rule: no source, no bullet.** If you cannot point at the file that produced a
number, delete the row. Do not round it up, do not estimate it, do not write "~". An
invented number is the one thing in an interview that cannot be recovered from, and
the follow-up question is always "how did you measure that?"

| From | Metric | Your number | Where it lives (file · test · trace) |
|------|--------|-------------|--------------------------------------|
| **W1 · bench** | Candidates benched | | |
| | Cost per successful parse, best vs worst | | |
| | Schema-hold rate of the local model | | |
| **W2 · RAG service** | Recall@k, vector-only vs hybrid+rerank | | |
| | Corpus size · chunk count | | |
| | P95 retrieval latency | | |
| **W3 · eval suite** | Golden-set size | | |
| | Faithfulness · context recall | | |
| | Judge agreement with your labels | | |
| | CI gate threshold, and what it blocks | | |
| **W4 · assistant** | Tools shipped · how many gated | | |
| | Step cap · timeout | | |
| | Task success rate on your own set | | |
| **W5 · memory + crew** | Context-budget reduction | | |
| | Cost cut from tiered delegation | | |
| | Memory TTL · provenance coverage | | |
| **W6 · hardened** | Red-team suite size | | |
| | Pass rate before vs after guardrails | | |
| | Gated tools fired under attack (should be 0) | | |
| **W7 · MCP** | Tools exposed · transport · auth | | |
| | Discovered-at-runtime, not hard-coded? | | |
| **W8 · deployed** | P50 · P95 · **P99** | | |
| | Cost per request, before vs after the ladder | | |
| | Cache hit rate · wrong-reuse count | | |
| | Time to roll back | | |

### Turn each one into a bullet

Noise is a responsibility. Signal is a measured outcome with the artifact behind it.

```
Noise:   Built a RAG chatbot
Signal:  RAG service: faithfulness 0.92, P95 480ms on a 50-question golden set,
         eval-gated in CI (W2, W3)

Noise:   Worked with AI agents
Signal:  Assistant with HITL approval on irreversible tools; 3-tier routing cut
         cost 52% at equal eval score (W4, W5)

Noise:   Deployed to production
Signal:  One-command stack, zero API keys; OTel-traced; P99 2.1s under a 3s
         budget, CI-gated on evals and red-team (W8)
```

Your three strongest, written out in full — these are the ones you will say most often:

```
1. ____________________________________________________________________________
2. ____________________________________________________________________________
3. ____________________________________________________________________________
```

```
Bullets on my resume with no number in them:  _____   ← target is 0
Headline:  ____________________________________________________________________
```

---

## Part 2 · The funnel

Update once a week, 15 minutes. Four ratios. This is the eval-first habit pointed at
your own job search, and it works for the same reason: you cannot fix a stage you have
not located.

| Week | Applied | Screens | Technicals | Onsites | Offers |
|:----:|:-------:|:-------:|:----------:|:-------:|:------:|
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |

```
Applied → screens     ____%     healthy ≳ 10–15%
Screens → technicals  ____%     healthy ≳ 50%
Technicals → onsites  ____%     healthy ≳ 50%
Onsites → offers      ____%     healthy ≳ 20–30%
```

### Read the leak

Find the **first** stage that is well below its band. That one, and only that one.

| Leaking stage | What it actually means | The fix |
|---------------|------------------------|---------|
| **Applied → screens** | Nobody is reading the work. Almost always the resume or the targeting, not the projects | Part 1 above: metric-first rewrite. Then check you are applying to roles that match your stack |
| **Screens → technicals** | The forty-minute story isn't landing, or fundamentals wobbled | Rehearse the system walkthrough out loud. Drill the qbank fundamentals section |
| **Technicals → onsites** | Producing answers under pressure, which is a different skill from knowing them | Daily reps, no notes, out loud. The spaced list is the signal for what to repeat |
| **Onsites → offers** | Usually the design round or the behavioural one | Recorded mocks against the rubric. STAR answers with a number in each |

```
Week of ________     Leaking stage: _______________________________________
The ONE fix I applied: ________________________________________________________
Re-measure on: ________     Did the number move?  [ ] yes  [ ] no  [ ] too early
```

**One fix at a time.** Rewrite the resume, change the targeting and add two projects in
the same week and you will not know which one moved the number — you will just have a
belief. You have spent a whole course learning not to do that.

Small numbers lie loudly. Four applications is not a 25% screen rate, it is one screen.
Give a stage at least 20 attempts before you conclude anything, exactly like reading a
P99 off 100 requests.

---

## Part 3 · The system that outlives the course

The course was your forcing function and it stops now. Write down what replaces it,
including the specific day — a habit without a slot is a resolution.

```
Skim weekly (changelogs, the MCP spec, 1–2 rigorous newsletters):
  ____________________________________________________  when: ______________

My personal eval set — the problem I care about enough to keep a golden.jsonl for:
  ____________________________________________________________________________
  (so every model release is a ten-minute experiment, not a vibes debate)

Building in public — next thing I ship or write:
  ____________________________________________________  by: ________________

Review date, when I check whether I actually did any of the above: ___________
```

Nobody keeps all three forever. Keep the eval set — it is the one that converts a
question you will be asked in every interview into a demonstration instead of a claim.
