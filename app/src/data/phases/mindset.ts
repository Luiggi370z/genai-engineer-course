// Generated from the shipped course bundle by scripts/extract-data.mjs.
// Edit freely from here on — this file is the source of truth for the content.

import { claim, sourceNote } from "../reference";
import type { PhaseContent } from "../types";

export const mindset: PhaseContent = {
  id: "p7",
  weeks: "Week 18 · ongoing",
  accent: { light: "#A04A08", dark: "#E07E32" },
  title: "The GenAI Mindset",
  tagline:
    "The field moves weekly and interviews test more than knowledge. This phase is about how to keep learning, how to practice, and how to turn everything you built into offers.",
  tldr: "A learning system for a field whose skills churn ~66% faster than average: the question bank rehearsed out loud until answers are reflexes, resume bullets carrying numbers mined from your own workshops, and the job search instrumented as a funnel you can fix one stage at a time.",
  objectives: [
    {
      id: "p7-o1",
      text: "**Design** a durable learning system for a field where skills churn ~66% faster than average",
    },
    {
      id: "p7-o2",
      text: "**Rehearse** the interview question bank out loud until the answers are reflexes",
    },
    {
      id: "p7-o3",
      text: "**Rewrite** your resume so every bullet carries a verifiable number, mined from your own workshops",
    },
    {
      id: "p7-o4",
      text: "**Diagnose** your job search as a funnel and fix the one stage that is actually leaking",
    },
  ],
  recall: [
    {
      id: "p7-r1",
      q: "An interviewer asks how you would cut the cost of a live GenAI feature. Give the levers in order, and say why the order is not negotiable.",
      a: "Cache, then route, then stream. Caching removes whole requests and is the most reversible change; routing sends easy work to a cheaper tier and must be reported alongside its eval score, or you have bought savings with quality; streaming changes perceived latency rather than cost. Out of order you get a system that is cheaper on the dashboard and worse for users — and “I would use a smaller model” as a first answer is the response that ends the topic early.",
      from: "p6-o5",
    },
    {
      id: "p7-r2",
      q: "How would you convince a skeptical stakeholder that a change you shipped actually improved the system? No notes.",
      a: "A committed baseline and a sliced golden set, with the judge calibrated against your own labels so the number means something, and a gate that would have blocked the change if it regressed. The receipts, not the vibes. This is also, word for word, the most valuable thing you can put on a resume — which is what the next hour is about.",
      from: "p-evals-o5",
    },
    {
      id: "p7-r3",
      q: "Why does MCP exist, in one sentence, and what does it replace?",
      a: "It turns an N×M integration problem into N+M: instead of every agent hand-rolling a client for every system, each system exposes one server and each agent speaks one protocol. It replaces bespoke per-agent tool code, not the tool-calling concept itself. Being able to say this cleanly in fifteen seconds is a small thing that signals a large one.",
      from: "p5-o1",
    },
  ],
  concepts: [
    {
      id: "p7-c1",
      title: "The mindset: verify, build, repeat",
      tag: "how to keep up",
      teaches: ["p7-o1"],
      blocks: [
        {
          kind: "p",
          text: 'The single most important habit this course tried to build isn’t a framework — it’s a **stance**: verify everything, benchmark on your own data, and trust the shape of a system over the name of a model. Model names in these pages will be stale within months; the patterns — provider-agnostic clients, hybrid + rerank, eval-first, containment, MCP — are the durable bets. That stance is also the honest answer to "how do you keep up?"',
        },
        {
          kind: "list",
          items: [
            "**Follow changelogs, not hype.** Vendor release notes, the MCP spec repo, a couple of rigorous newsletters. Skim weekly; go deep only when something touches your work.",
            "**Keep a personal eval set.** A growing `golden.jsonl` on a problem you care about turns every new model into a ten-minute experiment instead of a vibes debate.",
            '**Build in public.** A repo, a short write-up, a demo. It compounds — and it’s the strongest possible answer to "keep up" because you’re showing a system, not claiming heroics.',
            "**Skills churn ~66% faster in AI-exposed roles (PwC).** The premium is partly hazard pay for constant re-learning — which is exactly why the daily-reps habit below never retires.",
          ],
        },
        {
          kind: "callout",
          tone: "tip",
          title: "The through-line",
          text: "Everything you shipped — the RAG service, the assistant, the hardened agent, your own MCP, the deployment — is one connected system, and each piece was measured. That’s the portfolio *and* the mindset. You don’t have five demos; you have one system you can reason about end to end. That’s what senior looks like.",
        },
      ],
    },
    {
      id: "p7-c2",
      title: "Your job search is a funnel — instrument it",
      tag: "debug yourself",
      teaches: ["p7-o4"],
      blocks: [
        {
          kind: "predict",
          prompt:
            "Two hundred applications in, you have had four interviews and no offers. A friend tells you to rewrite your resume. Before reading on: is that the right fix, and what is the one thing you would need to know before spending a weekend on it?",
          answer:
            "You cannot tell, and the missing number is **how many of the 200 became screens**. If 40 did, your resume is working and the leak is downstream — the screen, the technical, the story. If 3 did, the resume or the targeting is the problem and your friend is right by accident. Same top-line numbers, opposite fixes, and one of them is a wasted weekend.",
          consolidation:
            "You already know this move: it is the stage-by-stage retrieval triage from Phase 2, pointed at yourself. “Two hundred applications, four interviews” is the aggregate score that hides which stage failed, exactly like a single accuracy number over a corpus. The advice you get about job searching is almost always someone else’s bottleneck generalised into a rule — and the same instinct that stops you tuning chunk size before checking whether the document is indexed at all is the one that stops you rewriting a resume that was never the problem.",
        },
        {
          kind: "p",
          text: "You spent this whole course learning to debug pipelines by finding the failing stage. Your search is the same shape. Track four numbers and fix only the stage that leaks — rejection is a metric, not a verdict.",
        },
        {
          kind: "flow",
          title: "Find the failing stage",
          nodes: [
            { label: "Applications → screens", sub: "leaking? fix resume + targeting" },
            { label: "Screens → technicals", sub: "leaking? fix the story + basics" },
            { label: "Technicals → onsites", sub: "leaking? drill the qbank + mocks" },
            { label: "Onsites → offers", sub: "leaking? design round + behaviorals" },
          ],
        },
        {
          kind: "p",
          text: "One stage at a time, one fix at a time, re-measure. The eval-first habit, pointed at yourself.",
        },
      ],
    },
    {
      id: "p7-c3",
      title: "Resume math: every claim needs a number",
      teaches: ["p7-o3"],
      blocks: [
        {
          kind: "table",
          headers: ["Noise", "Signal (mined from your workshops)"],
          rows: [
            [
              "Built a RAG chatbot",
              "RAG service: faithfulness 0.92, p95 480ms on a 50-Q golden set, eval-gated CI (Workshop 2)",
            ],
            [
              "Worked with AI agents",
              "Personal-assistant agent with HITL + least-privilege tools; 3-tier routing cut cost 52% (Workshops 4 & 6)",
            ],
            [
              "Familiar with MCP",
              "Authored an MCP server (3 tools, OAuth 2.1) consumed by my own agent via discovery (Workshop 7)",
            ],
            [
              "Deployed to production",
              "One-command stack (assistant + MCP + retrieval), CI-gated on evals + red-team, observable (Phase 8)",
            ],
          ],
        },
        {
          kind: "p",
          text: 'Every number on the right already exists in your workshop READMEs — mining them is an afternoon. Headline that matches reality: **"GenAI Engineer · RAG · Agents · MCP · evals/LLMOps · security."**',
        },
      ],
    },
    {
      id: "p7-c4",
      title: "The drill system",
      teaches: ["p7-o2"],
      blocks: [
        {
          kind: "list",
          items: [
            "**Daily (20 min):** 5 questions from the bank below, out loud, zero notes, self-graded against the reveal. Fumble one twice → spaced-repetition list.",
            "**Twice weekly (45 min):** a full Phase-6 design mock, recorded. Score against the 8 steps — anything you didn’t say out loud doesn’t count.",
            "**Weekly (15 min):** update the funnel numbers, pick ONE leaking stage, apply one fix.",
            "**Out loud matters:** recognizing an answer and producing one under pressure are different skills, and interviews only test the second.",
          ],
        },
      ],
    },
    {
      id: "p7-c5",
      title: "Money talk, with sources",
      tag: "fact-checked",
      teaches: ["p7-o3"],
      blocks: [
        {
          kind: "list",
          items: [
            '**The "56% AI wage premium" is real** — PwC’s Global AI Jobs Barometer (~1B job ads, verified 2026-07): AI-skilled workers average a 56% premium, up from 25% the prior year. Economy-wide context, not a personal promise.',
            "**India** (verified 2026-07): GenAI/LLM specialists ₹20–70 LPA mid-senior; strong-portfolio freshers ₹8–22; senior at product companies/GCCs up to ₹70 LPA–1 Cr+.",
            "**US** (verified 2026-07): base clusters ~$110–185K for typical/remote roles (ZipRecruiter, Glassdoor). Total comp at elite labs is another universe — Levels.fyi medians ~$555K at OpenAI, ~$665K at Anthropic.",
            "**Present numbers precisely, cite them, and date them** — salary data ages in months. Re-check the sources above before an interview loop; quoting a stale number precisely is worse than quoting a range honestly.",
          ],
        },
        { kind: "sources", ...sourceNote([claim("salary-premium"), claim("salary-bands")]) },
      ],
    },
  ],
  example: {
    title: "Field story: the funnel fix",
    text: "An engineer with strong workshops sent 90 applications and got 4 screens — then nearly rebuilt his portfolio in frustration. His funnel said otherwise: the projects were never seen because his resume led with responsibilities instead of numbers. One metric-first rewrite later, the same profile pulled a 22% screen rate. He’d been fixing the generate stage when the failure was in retrieval. Debug the stage that’s actually failing — in your pipelines and in your search.",
  },
  exercises: [
    {
      id: "p7-e1",
      title: "Daily reps",
      repo: "phase9-mindset/drill-deck",
      effort: { fast: 25, integration: null, realistic: 40 },
      rung: "faded",
      proves: "understand",
      task: "Five questions from the bank, out loud, no notes, self-graded. Every day. The bank doubles as your drill deck.",
      assesses: ["p7-o2"],
      solution: [
        "Consistency beats intensity: 20 minutes daily outperforms a 3-hour Sunday cram — retrieval practice is how reflexes form.",
      ],
    },
    {
      id: "p7-e2",
      title: "The metric-mining pass",
      repo: "phase9-mindset/resume",
      rung: "faded",
      proves: "implement",
      task: "Extract every number from your four workshop READMEs into resume bullets. Delete any bullet that survives without a number.",
      assesses: ["p7-o3"],
      solution: [
        "Faithfulness, recall, p95, cost-cut %, red-team pass rate, tools shipped — you generated them all; this is an afternoon of copy-editing.",
      ],
    },
    {
      id: "p7-e3",
      title: "Instrument the funnel",
      repo: "phase9-mindset/funnel-tracker",
      effort: { fast: 20, integration: null, realistic: 35 },
      rung: "faded",
      proves: "integrate",
      task: "Set up the 4-stage tracker. After 20 applications, name your leaking stage and apply exactly one fix.",
      assesses: ["p7-o4"],
      solution: [
        "Screens <10%? Resume/targeting. Technicals failing? Drill deck. Onsites failing? Mock the design round. One variable at a time — like any eval.",
      ],
    },
    {
      id: "p7-e4",
      title: "Blank editor: write your own next twelve weeks",
      rung: "independent",
      proves: "understand",
      task: "Blank page, no template, no example to imitate. Write the learning system you will actually run after this course ends: the sources you will read weekly and why those, the standing weekly slot where you build something small, how a claim gets verified before you repeat it, and the specific trigger that tells you a habit has lapsed. Then, on the same page, write your funnel’s four numbers as they stand today — even if three of them are zero — and name the one stage you will work on next and the one fix you will apply. One page. Date it, and put a review date on it.",
      assesses: ["p7-o1", "p7-o4"],
      solution: [
        "It names sources and says why those. “Follow AI Twitter” is not a system; a short list you chose, with a reason attached to each, is one you can prune when a source starts costing more attention than it returns.",
        "There is a recurring build slot with a time on it, not an intention to build things. The stance this whole course argued for — verify, build, repeat — collapses into passive reading the moment the build step has no place in the week.",
        "You wrote down how a claim gets checked. This is the actual content of the mindset: a benchmark on your own data, a small script, an eval row — something that turns “I read that X is faster” into “I measured X on my corpus.”",
        "There is a named lapse trigger. Every learning plan fails eventually; the ones that recover are the ones that told you in advance what failure would look like — two weeks with no build, a month without opening the drill deck.",
        "Your four funnel numbers are written down even where they are embarrassing or empty. A funnel you have not instrumented cannot tell you which stage leaks, and the whole argument of this phase is that you would otherwise fix the stage someone else told you about.",
        "It fits on one page and has a review date. A plan you will not reread is a document, not a system — and unlike every other task in this course, nobody is going to check this one but you.",
      ],
    },
  ],
  workshop: {
    id: "w-interview",
    title: "Workshop · The interview loop",
    subtitle:
      "The only workshop with no code, because the artifact is a habit: a scored design mock, a metrics sheet that traces every claim to a file, and a funnel with a fix attached.",
    repo: "workshops/interview-loop",
    doc: "WORKSHOP-INTERVIEW-LOOP.md",
    effort: { fast: 180, integration: null, realistic: 300 },
    proves: "understand",
    assesses: ["p7-o1", "p7-o2", "p7-o3", "p7-o4"],
    needs: ["p4-o1", "p4-o2", "p6-o5"],
    blocks: [
      {
        kind: "p",
        text: "Eight workshops in, you have a system: a bench, a retrieval service, an eval suite, an agent with memory and guardrails, an MCP server, and a deployment with traces and a cost ladder. You can also, right now, probably not explain it out loud for forty minutes without losing the thread. **That gap is the entire workshop.**",
      },
      {
        kind: "p",
        text: "It ships no code on purpose. Every deliverable is a **habit with an artifact attached**, because a habit with no artifact is a resolution, and resolutions do not survive week three. The course has been your forcing function for eighteen weeks and it stops now — what replaces it is the only part of this that still matters after the offer lands.",
      },
      {
        kind: "flow",
        title: "One loop, three cadences",
        nodes: [
          { label: "Daily · 20 min", sub: "5 qbank questions · out loud · no notes" },
          { label: "2×/week · 45 min", sub: "recorded mock → score the rubric" },
          { label: "Weekly · 15 min", sub: "funnel → name the leaking stage" },
          { label: "One fix", sub: "one variable, like any eval" },
          { label: "Re-measure", sub: "did the number move?" },
        ],
      },
      {
        kind: "callout",
        tone: "warn",
        title: "If it isn’t on the recording, it scores zero",
        text: "That is the rubric’s only rule and it is the reason mocks get recorded at all. “I know that” and “I would have said it with more time” are not answers an interviewer heard. Expect your first score to be bad — a first mock that scores well almost always means you scored it generously. The **trend across three mocks** is the deliverable, not the third score.",
      },
      {
        kind: "callout",
        tone: "tip",
        title: "No source, no bullet",
        text: "Every number on the metrics sheet must trace to a file, test or trace in one of your own repos. If it can’t, delete the row — don’t round it, don’t estimate it, don’t write “~”. An invented number is the one thing in an interview you cannot recover from, because the follow-up is always “how did you measure that?” The good news is that you generated all of them already; this is an afternoon of copy-editing.",
      },
      {
        kind: "p",
        text: "**Then the funnel, and the discipline it demands.** Four ratios, updated weekly, then pick the *one* leaking stage and apply *one* fix. Rewrite the resume, change the targeting and add two projects in the same week and you will not know which one moved the number — you will just have a belief. You spent a whole course learning not to do that. Small samples lie loudly too: four applications is not a 25% screen rate, it is one screen.",
      },
    ],
    deliverables: [
      {
        id: "w-interview-d1",
        text: "A **written weekly schedule** — drill, mock and metrics slots on specific days, each attached to a trigger that already happens",
        tier: "minimum",
      },
      {
        id: "w-interview-d2",
        text: "A **spaced-repetition list with real entries**, proving you drilled long enough to fumble something twice",
        tier: "full",
      },
      {
        id: "w-interview-d3",
        text: "**Three recorded design mocks**, each scored on the 8-step rubric, with the scores trending upward",
        tier: "minimum",
      },
      {
        id: "w-interview-d4",
        text: "Every rubric row scoring 0 or 1 has a **named drill and a date**, so a weakness becomes a task rather than an observation",
        tier: "full",
      },
      {
        id: "w-interview-d5",
        text: "A **metrics sheet where every claim traces to a file**, test or trace in your own repos — and anything that can’t is deleted",
        tier: "full",
      },
      {
        id: "w-interview-d6",
        text: "A **resume with a number in every bullet**, mined from that sheet; nothing survives without one",
        tier: "minimum",
      },
      {
        id: "w-interview-d7",
        text: "The **funnel with 20+ applications behind it**, the leaking stage named, and exactly one fix applied and dated",
        tier: "full",
      },
      {
        id: "w-interview-d8",
        text: "A **learning system that outlives the course**: what you skim weekly, the personal eval set you keep growing, what you build in public — plus the review date",
        tier: "full",
      },
    ],
    stretch: [
      "Swap mocks with someone. Self-scoring has a ceiling, and the ceiling is that you know what you meant — an outside scorer finds the step you think you covered and didn’t.",
      "Run the qbank against your own system: for each of the twenty answers, point at the file that proves you have done it. An answer with nothing behind it is a gap in the portfolio, not just in the drill.",
      "Keep the personal eval set on a problem you actually care about, so every model release is a ten-minute experiment. That is what turns “how do you keep up?” from a claim about your reading habits into a demonstration.",
      "Write the walkthrough — one post, one diagram, one honest failure section. It doubles as the forty-minute story, and it means you have built in public at least once.",
    ],
  },
  checkpoint: [
    {
      id: "p7-q1",
      q: 'How do you answer "how do you keep up with a field moving this fast?"',
      a: "Show a system, not heroics: changelogs and the MCP spec skimmed weekly, a growing personal eval set that turns each new model into a ten-minute experiment, and building in public. The verify-everything, benchmark-on-your-own-data stance is the real answer.",
      demands: ["constraints", "evidence"],
    },
    {
      id: "p7-q2",
      q: "Your search is stalling. How do you diagnose it like a pipeline?",
      a: "Treat it as a funnel and find the failing stage: applications→screens (fix resume/targeting), screens→technicals (fix story/basics), technicals→onsites (drill the bank + mocks), onsites→offers (design round + behaviorals). Fix one stage, re-measure. Rejection is a metric, not a verdict.",
      demands: ["evidence", "failure-modes"],
    },
    {
      id: "p7-q3",
      q: "What turns a resume bullet from noise into signal?",
      a: 'A verifiable number. "Built a RAG chatbot" is noise; "RAG service, faithfulness 0.92, p95 480ms, eval-gated CI" is signal — and every such number already exists in your workshop READMEs.',
      demands: ["alternatives", "evidence"],
    },
  ],
  qbank: [
    {
      group: "LLM fundamentals",
      items: [
        {
          id: "qb-1",
          q: "Temperature vs top_p?",
          a: "Temperature rescales the whole distribution; top_p truncates to the probability nucleus. Tune one, never both. 0–0.2 for extraction/tools, 0.7+ for creative work.",
        },
        {
          id: "qb-2",
          q: "What is a KV cache and why does it matter?",
          a: "It caches attention keys/values for generated tokens so each new token doesn’t recompute over the whole sequence — central to latency, throughput, and why long contexts cost what they do.",
        },
        {
          id: "qb-3",
          q: "How do you count tokens and cost correctly in 2026?",
          a: "Count with the vendor’s own counter before sending (Anthropic’s free count_tokens, tiktoken for OpenAI, Gemini’s API — tiktoken undercounts Claude 15–20%). Measure real cost from the response’s usage object, including cached and reasoning tokens.",
        },
        {
          id: "qb-4",
          q: "When do you serve a model locally?",
          a: "Privacy/data residency, offline, zero marginal cost for high-volume cheap tasks, free dev loops. You trade the quality ceiling, window size, and tool-calling reliability — and you own the ops.",
        },
      ],
    },
    {
      group: "RAG",
      items: [
        {
          id: "qb-5",
          q: "Why hybrid over vector-only?",
          a: "Dense embeddings shred exact identifiers into meaningless sub-tokens; keyword search (BM25) catches them. Fuse with RRF, then rerank for precision.",
        },
        {
          id: "qb-6",
          q: "RAG vs fine-tuning?",
          a: "RAG for fresh/large/changing knowledge; fine-tune (LoRA/QLoRA) for format, style, and domain vocabulary; combine when you need both.",
        },
        {
          id: "qb-7",
          q: "How do you evaluate RAG?",
          a: "Golden set + RAGAS (faithfulness + context recall first), pinned judge, CI gate, online sampling. Then sketch the harness — you built it in Phase 3 and shipped it in Workshop 3.",
        },
        {
          id: "qb-8",
          q: "A RAG answer is wrong — how do you find the failing stage?",
          a: "Work back-to-front: does the answer ignore its context (writer/prompt)? Is the right doc even indexed (ingestion)? Indexed but ranked low (retrieval — add hybrid, check embedding-model match)? Retrieved but buried (add a reranker)? Re-run the eval after each change.",
        },
      ],
    },
    {
      group: "Agents",
      items: [
        {
          id: "qb-9",
          q: "What makes something an agent, and what are its safety rails?",
          a: "A model in a loop with tools: reason → act → observe, until done. Rails: step cap and wall-clock timeout in CODE, sandboxed tools, least privilege, HITL on irreversible actions, graceful degradation.",
        },
        {
          id: "qb-10",
          q: 'Critique "expensive model routes, cheap model works."',
          a: "Backwards for most traffic: triage is easy — do it cheap or free (local), escalate the hard fraction. Invert only when planning is the hard part. Per-node model choice is config.",
        },
        {
          id: "qb-11",
          q: "When LangGraph vs Pydantic AI vs CrewAI?",
          a: "LangGraph for durability/branching/HITL (the production default); Pydantic AI for a clean, type-safe single agent with minimal ceremony; CrewAI for fast role-based multi-agent prototyping. Choose by your dominant constraint.",
        },
        {
          id: "qb-12",
          q: "Why is a tool’s docstring the interface?",
          a: "The model picks and fills a tool using only its name, docstring, and type hints. A vague docstring is a vague API — say what it does and when to use it, written like a prompt. Same principle powers MCP tool discovery.",
        },
      ],
    },
    {
      group: "MCP",
      items: [
        {
          id: "qb-13",
          q: "MCP vs plain tool calling?",
          a: "MCP adds runtime discovery and standard transports on top of tool calling — write the server once, any compliant client uses it. In-memory in tests, stdio locally, Streamable HTTP remotely. Since the 2026-07-28 spec it is stateless request/response, so the five beats still describe what a client does but nothing is held open between them.",
        },
        {
          id: "qb-14",
          q: "The five beats of an MCP client session?",
          a: "Connect → initialize → list_tools/resources → call_tool/read_resource → close. Every client repeats exactly this.",
        },
        {
          id: "qb-15",
          q: "MCP auth by deployment — and the confused-deputy trap?",
          a: "stdio → none (env-var secrets); internal remote → Bearer/API key over HTTPS; public → OAuth 2.1 + PKCE with audience validation. Never forward the client’s token upstream — obtain your own; that’s the confused-deputy vulnerability.",
        },
      ],
    },
    {
      group: "System design & security",
      items: [
        {
          id: "qb-16",
          q: 'Direct vs indirect prompt injection, and why is injection "unsolved"?',
          a: "Direct: user types the malice. Indirect: it hides in data the agent reads (email/web/docs), user is the victim — the 2026 nightmare. It’s structural because instructions and data share one channel, so the strategy is containment (least privilege + HITL + output gates), not filtering.",
        },
        {
          id: "qb-17",
          q: "How do you evaluate a GenAI system in production?",
          a: "Offline golden-set regression in CI, online monitoring (sampled faithfulness, LLM-as-judge, user signals), and per-query cost/latency tracing from the usage object.",
        },
        {
          id: "qb-18",
          q: "Name three prompt-attack families and one defense each.",
          a: "Indirect injection → spotlighting + guard retrieved content + HITL. Obfuscation/encoding → decode-and-normalize before scanning + a guard model. Multi-turn (Crescendo) → evaluate the conversation not just the last turn + output gate every turn.",
        },
      ],
    },
    {
      group: "Behavioral",
      items: [
        {
          id: "qb-19",
          q: "Tell me about a time an LLM feature failed.",
          a: "STAR with a number: what broke (hallucination/cost/latency/injection), how you MEASURED it, the fix, the metric that moved. Your break-and-fix drills and red-team runs are real material.",
        },
        {
          id: "qb-20",
          q: "How do you keep up with a field moving this fast?",
          a: "Show a system, not heroics: changelogs and the MCP spec weekly, a growing personal eval set, building in public. The verify-everything habit from this course is the answer.",
        },
      ],
    },
  ],
  resources: [
    {
      label: "PwC Global AI Jobs Barometer",
      url: "https://www.pwc.com/gx/en/issues/artificial-intelligence/ai-jobs-barometer.html",
    },
    { label: "Levels.fyi — AI/ML compensation", url: "https://www.levels.fyi" },
    { label: "Glassdoor — GenAI engineer salaries", url: "https://www.glassdoor.com" },
    {
      label: "Simon Willison’s blog — stay-current reading",
      url: "https://simonwillison.net",
    },
  ],
};
