# Design-mock rubric

Score one recorded mock. Copy this file per attempt (`mock-01.md`, `mock-02.md`) so the
trend is visible — three scored mocks tell you more than one perfect one.

```
Date:            ____________________     Duration:  _______ min  (target 25–35)
Prompt:          ______________________________________________________________
Recorded?        [ ] yes   ← if no, stop. An unrecorded mock cannot be scored.
```

**The scoring rule, and it is the entire point:** if it is not on the recording, it
scores **0**. Not "I know that", not "I would have said it with more time". Interviews
score what you said. So does this.

| Score | Means |
|:-----:|-------|
| **0** | Never came up |
| **1** | Mentioned, but as a word — no specifics, no reasoning, would not survive one follow-up |
| **2** | Covered with a real decision and a reason, and you could defend it if pushed |

## The eight steps

Same script as Phase 4, in the same order. The order matters: clarifying after you have
drawn boxes is a different (worse) answer than clarifying before.

| # | Step | What a **2** sounds like | Score | Note to self |
|:-:|------|--------------------------|:-----:|--------------|
| 1 | **Clarify before drawing** | Four or more questions before a single box: QPS, P95 target, freshness, multi-tenancy, PII and residency — and residency asked *because* it might force self-hosted models | ☐ | |
| 2 | **Split ingestion from serving** | Two pipelines drawn separately, with what triggers the batch side and what runs per request stated out loud | ☐ | |
| 3 | **Retrieval** | Hybrid plus rerank as the default *with the reason* (dense shreds exact identifiers), and tenant isolation via namespaces or metadata filters | ☐ | |
| 4 | **Evaluation** | A golden set, the two metrics you gate on first, and where the gate lives in CI — unprompted | ☐ | |
| 5 | **Observability** | Tracing plus cost per query, named tooling, and the OTel-portability argument for why the backend is swappable — unprompted | ☐ | |
| 6 | **Cost levers, in order** | Cache → route → stream, ordered by *risk* not by size, with the behaviour-preserving rungs taken first | ☐ | |
| 7 | **Failure modes with mitigations** | Injection, hallucination, loops, rate limits, PII leaks, cost runaway — each with a named, specific defense | ☐ | |
| 8 | **Security as a built layer** | Least privilege, HITL on irreversible actions, spotlighting untrusted content, an output gate — described as code you wrote, not as a policy | ☐ | |

**Steps 4 and 5 are the ones candidates skip.** Naming evaluation and observability
without being asked is the clearest senior signal in the whole script, which is why
they are worth watching for specifically. If either scores 0 twice in a row, that is
not a nerves problem, it is a script problem — put them on an index card.

## Delivery

Content is most of the grade, but a correct design delivered badly still loses the
round.

| Dimension | What a **2** looks like | Score |
|-----------|-------------------------|:-----:|
| **Structure** | An audible spine. The interviewer can tell which step you are on without asking | ☐ |
| **Numbers** | Estimates with units and a stated assumption, not "it should be fast enough" | ☐ |
| **Trade-offs** | At least two decisions presented as a choice with a cost, not as the only option | ☐ |
| **Under pushback** | One challenge absorbed and answered without either caving or getting defensive | ☐ |
| **Time** | Finished inside the window with the security layer covered, not sprinting through step 8 at minute 34 | ☐ |
| **Silence** | Thinking out loud instead of going quiet, and comfortable saying "I don't know, here is how I'd find out" | ☐ |

```
Steps    ___ / 16          Delivery  ___ / 12          Total  ___ / 28
```

Rough reading: below 14 you are missing steps, not polish — rehearse the script itself.
14–21 is a survivable round with visible gaps. Above 21, start recording harder prompts
(multi-tenant, untrusted documents, a hard P99 budget) rather than repeating this one.

## The part that turns a score into practice

Every row that scored **0 or 1** goes here, with a drill and a date. A rubric that ends
at the total is a diary entry.

| Row | Score | What I'll actually do about it | By |
|-----|:-----:|--------------------------------|----|
| | | | |
| | | | |
| | | | |

```
The one thing I'll do differently in the next mock:
_______________________________________________________________________________

Something I said that I could NOT defend if pushed (there is always one):
_______________________________________________________________________________
```
