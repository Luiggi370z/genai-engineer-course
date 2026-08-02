import type { PhaseContent } from "../types";

// `id` is a stable storage key, not a phase number — the number comes from the
// order in phases/index.ts, so inserting a phase never breaks saved progress.
export const evals: PhaseContent = {
  id: "p-evals",
  weeks: "Weeks 5–6",
  color: "#4D7C0F",
  title: "Prove It Works: Evals & Judges",
  tagline:
    "Anyone can demo a RAG service. This phase is how you earn the right to say “it works” — a golden set you can defend, a judge you calibrated yourself, and a gate that blocks the merge when the number drops.",
  tldr: "A sliced golden set with provenance and abstention cases, a judge you calibrate against your own labels with Cohen’s κ, trajectory scoring for agents, and a merge gate on a committed baseline — a fast smoke run per PR, the full suite nightly.",
  objectives: [
    {
      id: "p-evals-o1",
      text: "**Construct** a sliced golden dataset over your own corpus — with provenance, abstention cases, and a leakage check",
    },
    {
      id: "p-evals-o2",
      text: "**Run** LLM-as-judge scoring with the current RAGAS API, and name the four ways a judge lies to you",
    },
    {
      id: "p-evals-o3",
      text: "**Calibrate** a judge against your own human labels (agreement + Cohen’s κ) and choose thresholds from the data",
    },
    {
      id: "p-evals-o4",
      text: "**Evaluate** an agent’s *trajectory* — tool choice and goal completion — not just its final message",
    },
    {
      id: "p-evals-o5",
      text: "**Gate** merges on a committed baseline: a fast per-PR smoke gate, a full nightly run, and a prod sampling loop that feeds new rows back in",
    },
  ],
  recall: [
    {
      id: "p-evals-r1",
      q: "Name the two metrics you would keep if you could only afford two, and say which component each one blames.",
      a: "Faithfulness blames the writer — the model ignored or embellished the context it was given. Context recall blames the librarian — retrieval never found the right passage. Between them they sort every failure into “generation” or “retrieval,” which is the first fork in any debugging session. This phase is about making both numbers trustworthy enough to gate a merge on.",
      from: "p2-o3",
    },
    {
      id: "p-evals-r2",
      q: "A chunk arrives in the model’s context but the answer ignores it anyway. Which stage do you suspect, and which stage do you rule out?",
      a: "Rule out retrieval — it did its job. Suspect the writer: a weak model, a prompt that does not insist on grounding, temperature too high, or the passage buried mid-context where attention thins out. The reason this matters here is that a judge scoring the final answer alone would blame retrieval, and you would spend a week tuning the wrong stage.",
      from: "p2-o4",
    },
    {
      id: "p-evals-r3",
      q: "From Phase 1: which field tells you what an eval run actually cost, and why does that number decide how you design this phase’s gates?",
      a: "The `usage` object on each response. It matters because a judged eval is itself a pile of LLM calls — running 500 rows through a frontier judge on every pull request is a real bill and a slow gate. That constraint is exactly why the design below is two gates rather than one: a cheap deterministic tier per push, the expensive judged tier nightly.",
      from: "p1-o2",
    },
  ],
  concepts: [
    {
      id: "p-evals-c1",
      title: "The golden set is the product",
      tag: "dataset engineering",
      teaches: ["p-evals-o1"],
      blocks: [
        {
          kind: "predict",
          prompt:
            "Building 50 golden questions by hand is slow, so you do the obvious thing: feed each indexed chunk to a model and ask it to write a question that chunk answers. Five hundred rows in twenty minutes. You run your Phase 2 harness and context recall comes back at **0.97**. Before reading on — is your retrieval excellent, and if not, what exactly did you just measure?",
          answer:
            "You measured that a chunk can retrieve a question written from itself. Every question is answerable by construction, phrased in the source passage’s own vocabulary, and guaranteed to have its answer already in the index — so you have eliminated the three things that break real retrieval: paraphrase, absence, and multi-hop. That 0.97 would hold steady while your production system got worse.",
          consolidation:
            "This is **leakage**, and it is the single most common way a serious-looking eval suite ends up measuring nothing. It is also why objective 1 asks for three specific things rather than a row count: *provenance*, so you can see which questions came from where; *abstention cases*, whose answers are deliberately not in the corpus; and an explicit *leakage check* for questions that overlap their source too closely. Generated rows are still useful — as a first draft you then read, cut, and rephrase. Fifty questions you have personally believed are worth more than five hundred you have not.",
        },
        {
          kind: "p",
          text: "Every eval number you will ever quote is a **property of your question set**, not of your system. Change the questions and the score moves; that is not cheating, it is the definition. So the dataset gets the engineering discipline you would give production code: it is reviewed, versioned, sliced, and frozen. Fifty good questions beat five thousand scraped ones, because you can read fifty and *believe* them.",
        },
        {
          kind: "table",
          headers: ["Slice", "What a failure here means", "Rough share of a 50-row set"],
          rows: [
            ["Semantic", "Paraphrase understanding broke — embeddings or chunking", "~20 rows"],
            [
              "Exact / identifier",
              "Keyword arm is missing or broken (`INV-88231`, statute numbers, error codes)",
              "~12 rows",
            ],
            [
              "Multi-hop",
              "One chunk was never going to be enough — retrieval depth or query rewriting",
              "~8 rows",
            ],
            [
              "Unanswerable",
              "**The abstain path failed** — the system invented an answer the corpus can’t support",
              "~7 rows",
            ],
            [
              "Adversarial",
              "A plausible-but-wrong neighbour outranked the truth (near-duplicate docs, stale versions)",
              "~3 rows",
            ],
          ],
        },
        {
          kind: "callout",
          tone: "warn",
          title: "The unanswerable slice is non-negotiable",
          text: "A set of only answerable questions rewards a system that always answers. Your abstain path is the single most business-relevant behaviour you have, and it is invisible to a golden set that never tests it. Score a correct “not in the docs” as a **pass**.",
        },
        {
          kind: "code",
          title: "One golden row, with its paperwork",
          code: `{"id": "g-014",
 "slice": "exact",
 "question": "Which invoice does the March credit note INV-88231 offset?",
 "ground_truth": "Invoice INV-88102, dated 2026-02-19.",
 "expects_abstention": false,
 "supporting_doc_ids": ["ap-2026-03.pdf#p4"],
 "source": "prod log 2026-07-14, user asked it three times and got junk",
 "labeled_by": "you", "labeled_on": "2026-07-15"}

# supporting_doc_ids  -> lets you compute retrieval metrics with NO judge at all
# source              -> every row justifies its existence; no row is decoration
# expects_abstention  -> the abstain slice becomes machine-checkable`,
        },
        {
          kind: "list",
          items: [
            "**Every production bug becomes a row.** That single habit is what turns an eval suite into an asset instead of a chore.",
            "**Freeze and version it** (`golden.v3.jsonl`). Editing rows to make yesterday’s failure pass is the most common self-deception in this whole discipline.",
            "**Check for leakage** before you trust a score: a question whose wording is lifted verbatim from a chunk measures string matching, not retrieval. Near-duplicate detection catches both leakage and accidental copy-paste rows.",
            "**Hold back a slice you never tune against.** If you tune chunking against all 50 rows, all 50 rows are now training data.",
            "**Label the hard ones yourself.** Generating questions with an LLM is fine for volume; the ground truth still has to be defensible by a human in a review.",
          ],
        },
      ],
    },
    {
      id: "p-evals-c2",
      title: "LLM-as-judge, and the four ways it lies",
      tag: "core",
      teaches: ["p-evals-o2"],
      blocks: [
        {
          kind: "p",
          text: "A judge is just a model asked to output a score instead of an answer — which means it inherits every failure mode of a model, and adds a few of its own. That is not a reason to avoid it; graders that read meaning are the only way to score open-ended text at any scale. It *is* a reason to treat the judge as **part of your measuring instrument** and hold it to the same standard: pinned, documented, and checked against something you trust.",
        },
        {
          kind: "table",
          headers: ["How it lies", "What you see", "What you do about it"],
          rows: [
            [
              "**Position bias**",
              "In A/B comparisons, whichever answer is shown first wins suspiciously often",
              "Score each candidate on its own, or run both orders and average",
            ],
            [
              "**Verbosity bias**",
              "The longer, more confident answer scores higher regardless of support",
              "Score against retrieved context claim-by-claim, not on overall impression",
            ],
            [
              "**Self-preference**",
              "The judge prefers text written by its own model family",
              "Never let the judge and the generator be the same pinned model",
            ],
            [
              "**Silent drift**",
              "Scores move week to week with zero code change",
              "Pin model + version + temperature 0 + prompt; re-run last week’s set to confirm",
            ],
          ],
        },
        {
          kind: "callout",
          tone: "warn",
          title: "Cheap metrics first, judge second",
          text: "Retrieval metrics that need **no judge at all** — did the supporting doc appear in the top-k? — are free, deterministic, and catch the majority of RAG regressions. Spend judge tokens only on what genuinely needs to read meaning: faithfulness and answer quality. A suite that needs an LLM to tell you the index is empty is a badly designed suite.",
        },
        {
          kind: "code",
          title: "Faithfulness + context recall, current RAGAS API",
          code: `# ragas 0.4.x: the metric classes live in ragas.metrics.collections and take an
# explicit judge. (Importing from ragas.metrics still works but is deprecated.)
from openai import AsyncOpenAI
from ragas.llms import llm_factory
from ragas.metrics.collections import ContextRecall, Faithfulness

judge = llm_factory(                      # pinned, and free on Ollama
    "qwen3-coder:30b",                    # the verified default in src/
    client=AsyncOpenAI(base_url="http://localhost:11434/v1", api_key="ollama"),
    temperature=0,
)

faithfulness = Faithfulness(llm=judge)
recall = ContextRecall(llm=judge)

f = await faithfulness.ascore(user_input=q, response=answer,
                              retrieved_contexts=contexts)
r = await recall.ascore(user_input=q, retrieved_contexts=contexts,
                        reference=ground_truth)
print(f.value, r.value)

# faithfulness low   -> the WRITER strayed from its context (hallucination)
# context_recall low -> the LIBRARIAN never fetched the needed chunk`,
        },
        {
          kind: "callout",
          tone: "fix",
          title: "Write the rubric like a spec, not a vibe",
          text: "“Rate the answer 1–5 for quality” produces noise. “Return **pass** only if every claim in the answer is supported by the provided context; a claim that is true but absent from the context is a **fail**” produces a signal you can calibrate. Binary or three-way verdicts with an explicit failure definition beat 1–5 scales — humans can’t agree on a 5-point scale either, which is exactly why your κ will be terrible if you use one.",
        },
      ],
    },
    {
      id: "p-evals-c3",
      title: "Calibrate the judge, or your dashboard is decoration",
      tag: "the part almost nobody teaches",
      teaches: ["p-evals-o3"],
      blocks: [
        {
          kind: "p",
          text: "Here is the question that separates people who *run* evals from people who *trust* them: **how do you know the judge is right?** The only honest answer is that you labeled some of it yourself and measured how often the judge agreed with you. That measurement is the calibration, and it is a one-afternoon job that permanently changes how much weight your numbers can carry.",
        },
        {
          kind: "flow",
          title: "The calibration loop",
          shape: "cycle",
          nodes: [
            { label: "Label ~50 rows by hand", sub: "pass / fail, with a written rule" },
            { label: "Run the judge on the same rows", sub: "temperature 0, pinned" },
            { label: "Measure agreement + κ", sub: "not accuracy — κ" },
            { label: "Read the disagreements", sub: "they name the flaw in the rubric" },
            {
              label: "Fix the rubric or the threshold",
              sub: "then round again on a fresh slice — freeze only once κ holds, and record it next to every score",
            },
          ],
        },
        {
          kind: "callout",
          tone: "warn",
          title: "Raw agreement is a liar when classes are imbalanced",
          text: "If 92% of your rows are passes, a judge that says “pass” to everything scores 92% agreement and has learned nothing. **Cohen’s κ** corrects for agreement you would get by chance — it is the number to report. A judge with 92% agreement and κ ≈ 0 is a rubber stamp.",
        },
        {
          kind: "table",
          headers: ["Cohen’s κ (vs your labels)", "Read it as", "What to do next"],
          rows: [
            [
              "below ~0.2",
              "The judge is measuring something else entirely",
              "Rewrite the rubric — usually the failure definition is missing or the scale is too fine",
            ],
            [
              "~0.2 – 0.4",
              "Weak signal; fine for smoke-testing, not for gating",
              "Simplify to a binary verdict, add 2–3 worked examples to the prompt",
            ],
            [
              "~0.4 – 0.6",
              "Usable with a margin; treat small deltas as noise",
              "Gate on regressions larger than the disagreement band, not on absolutes",
            ],
            [
              "above ~0.6",
              "Substantial agreement — you can gate merges on this",
              "Freeze judge + rubric together and re-calibrate whenever either changes",
            ],
          ],
        },
        {
          kind: "p",
          text: "(Those bands are the long-standing Landis & Koch convention from inter-rater reliability research, not a law of nature. Use them to decide *how much* to trust the judge, not to congratulate yourself.)",
        },
        {
          kind: "code",
          title: "Agreement, κ, and the threshold you should actually pick",
          code: `from sklearn.metrics import cohen_kappa_score

human  = [r["human"] for r in rows]                 # "pass" / "fail", by you
judge_ = [r["judge"] for r in rows]                 # same rows, pinned judge

agreement = sum(h == j for h, j in zip(human, judge_)) / len(rows)
kappa = cohen_kappa_score(human, judge_, labels=["pass", "fail"])
print(f"agreement {agreement:.2f}  kappa {kappa:.2f}")   # report BOTH

# For a numeric judge, don't accept 0.5 because it's round -- sweep it:
best = max(
    (cohen_kappa_score(human, ["pass" if s >= t else "fail" for s in scores],
                       labels=["pass", "fail"]), t)
    for t in [i / 20 for i in range(1, 20)]
)
print("best kappa", best[0], "at threshold", best[1])

# Then READ the disagreements. Every one is either a bad rubric, a bad label,
# or a genuinely ambiguous question that should not be in the golden set.`,
        },
        {
          kind: "callout",
          tone: "tip",
          title: "Calibration is also how you buy a cheaper judge",
          text: "Calibrate the free local judge against your labels **and** against a big hosted one on the same rows. If κ holds up, you have just justified running evals on every PR for zero marginal cost — with a written receipt for the decision. That receipt is a great interview answer.",
        },
      ],
    },
    {
      id: "p-evals-c4",
      title: "Agents: score the trajectory, not just the last message",
      tag: "agent evals",
      teaches: ["p-evals-o4"],
      blocks: [
        {
          kind: "p",
          text: "For a single-turn RAG answer, the output *is* the behaviour. For an agent, the output hides the behaviour: an assistant that answered correctly after calling `delete_calendar_event` and getting lucky is a latent incident, not a pass. So you score the **trajectory** — which tools it chose, in what order, with what arguments, and whether the user’s actual goal was met.",
        },
        {
          kind: "table",
          headers: ["What to score", "The question it answers", "Needs a judge?"],
          rows: [
            [
              "Tool-call accuracy / F1",
              "Did it call the tools it should have — and none it shouldn’t?",
              "**No** — pure comparison against reference calls",
            ],
            [
              "Argument correctness",
              "Right tool, right arguments? (`send_email(to=wrong_person)`)",
              "**No** — structural check",
            ],
            [
              "Goal accuracy",
              "Did the conversation end with the user’s goal actually achieved?",
              "Yes — needs to read the transcript",
            ],
            [
              "Topic adherence",
              "Did it stay inside its remit, or answer things it shouldn’t?",
              "Yes",
            ],
            [
              "Step economy",
              "Six tool calls for a one-call task = cost and latency bug",
              "**No** — count them",
            ],
          ],
        },
        {
          kind: "callout",
          tone: "tip",
          title: "Half of agent eval is free and offline",
          text: "Trajectory metrics compare structures, so they run in CI with no model, no key and no network — the same tier as your unit tests. Build these first: they catch the regressions that actually page you (wrong tool, wrong argument, unapproved side effect) and they cost nothing.",
        },
        {
          kind: "code",
          title: "A trajectory test that runs in your fast suite",
          code: `from ragas.messages import AIMessage, HumanMessage, ToolCall
from ragas.metrics.collections import ToolCallAccuracy

# No llm= argument: this metric never calls a model.
metric = ToolCallAccuracy()

conversation = [
    HumanMessage(content="what's on my calendar tomorrow?"),
    AIMessage(content="checking",
              tool_calls=[ToolCall(name="list_events", args={"day": "tomorrow"})]),
]

result = metric.score(
    user_input=conversation,
    reference_tool_calls=[ToolCall(name="list_events", args={"day": "tomorrow"})],
)
assert result.value == 1.0     # strict_order=False if order shouldn't matter

# The high-value assertion in the same suite: the DANGEROUS tool never fires
# without approval. That's a one-line trajectory check on a poisoned input.`,
        },
      ],
    },
    {
      id: "p-evals-c5",
      title: "Two gates and a sampling loop",
      tag: "in CI, or it didn’t happen",
      teaches: ["p-evals-o5"],
      blocks: [
        {
          kind: "p",
          text: "An eval you run by hand when you remember to is a vibe with extra steps. The discipline is boring and mechanical: a **fast gate** on every PR that a developer will never route around, a **full run** nightly, a **committed baseline** so “did it get worse?” is a diff and not an argument, and a **sampling loop** from production that keeps the golden set honest as real traffic drifts away from it.",
        },
        {
          kind: "table",
          headers: ["Gate", "When", "Budget", "What it blocks"],
          rows: [
            [
              "Smoke gate (no judge)",
              "Every PR, every push",
              "under ~60s",
              "Empty index, broken retrieval, missing abstain path, wrong tool calls",
            ],
            [
              "Judged gate (subset)",
              "Every PR touching prompts, retrieval or the model",
              "a few minutes",
              "Faithfulness regressions on the ~10-row smoke slice",
            ],
            [
              "Full suite + baseline diff",
              "Nightly and pre-release",
              "unbounded",
              "Any metric or slice regression beyond tolerance",
            ],
            [
              "Prod sampling review",
              "Weekly, a handful of real traces",
              "human time",
              "Nothing — it *generates* the next golden rows and the next bug",
            ],
          ],
        },
        {
          kind: "code",
          title: "The gate: absolute bars AND a regression check",
          code: `# evals/baseline.json is COMMITTED. It's the "did we get worse" reference.
BARS = {"faithfulness": 0.85, "context_recall": 0.80}
TOLERANCE = 0.03            # below your judge's disagreement band = noise

def gate(scores: dict[str, float], baseline: dict[str, float]) -> list[str]:
    fails = [f"{m} {scores[m]:.2f} < bar {bar}"
             for m, bar in BARS.items() if scores[m] < bar]
    fails += [f"{m} regressed {baseline[m]:.2f} -> {scores[m]:.2f}"
              for m in baseline
              if scores[m] < baseline[m] - TOLERANCE]
    return fails                          # non-empty  =>  CI fails the merge

# Per-SLICE gates too: an overall 0.86 can hide the unanswerable slice
# collapsing from 1.00 to 0.40. Averages are where regressions go to hide.`,
        },
        {
          kind: "callout",
          tone: "fix",
          title: "Absolute bars and deltas catch different bugs",
          text: "A bar alone lets you rot slowly from 0.94 to 0.86 with every PR passing. A delta alone lets a badly-broken system stay broken as long as it doesn’t get *worse*. You need both, and the tolerance has to be wider than the noise you measured during calibration — otherwise CI cries wolf and someone adds `--no-verify` to their muscle memory.",
        },
        {
          kind: "flow",
          title: "The loop that keeps the suite alive",
          nodes: [
            { label: "Prod traffic", sub: "trace every request" },
            { label: "Sample", sub: "random + low-confidence + thumbs-down" },
            { label: "Human review", sub: "20 minutes, weekly" },
            { label: "New golden rows", sub: "bugs become permanent tests" },
            { label: "Re-baseline", sub: "deliberately, in a reviewed PR" },
          ],
        },
      ],
    },
  ],
  example: {
    title: "Field story: the 0.91 that meant nothing",
    text: "A team shipped a support-answer bot behind a faithfulness gate of 0.85 and sat comfortably at 0.91 for a month while complaints climbed. The golden set had been generated *from the indexed chunks*, so every question was answerable by design and the abstain path had never once been tested — in production, a third of real questions were about a product tier that wasn’t in the corpus at all, and the bot cheerfully made things up. Adding twelve unanswerable rows dropped the score to 0.62 overnight. Nothing about the system had changed; they had simply started measuring the thing that was broken.",
  },
  exercises: [
    {
      id: "p-evals-e1",
      title: "Build a golden set you can defend",
      repo: "phase3-evals/01-golden-set",
      rung: "faded",
      proves: "implement",
      task: "Take the corpus behind your Workshop-2 RAG service and write golden rows across the five slices — including the unanswerable ones — in three sittings of **10, 25 and 50**, scoring at each. Then write the *dataset* tests: no near-duplicates, no verbatim leakage from a chunk, every slice populated, every row carrying its provenance.",
      assesses: ["p-evals-o1"],
      needs: ["p2-o3"],
      solution: [
        "Test the dataset before you test the system. A suite whose fixture is broken produces confident nonsense.",
        "Score at 10, 25 and 50 — the milestones are what keep this from being the task everyone abandons, and the interval at each is the actual lesson. 8 of 10 is not 0.80; it is 0.80 with a 95% interval of roughly 0.49–0.94, which a mediocre system produces routinely. Ten rows still finds your obvious bugs on day one. It is just not a number you may quote yet, and by row 50 you will have watched the interval close.",
        "Near-duplicate detection with `rapidfuzz` catches both accidental copy-paste and the leakage case where a question is lifted from the chunk it should be retrieving.",
        "Store `supporting_doc_ids` on every answerable row — that one field gives you judge-free retrieval metrics forever.",
      ],
      code: `# evals/dataset.py — the golden set gets tests of its own
from rapidfuzz import fuzz

SLICES = {"semantic", "exact", "multi_hop", "unanswerable", "adversarial"}

def near_duplicates(rows, threshold=92.0):
    out = []
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            if fuzz.token_set_ratio(a["question"], b["question"]) >= threshold:
                out.append((a["id"], b["id"]))
    return out

def leaked(rows, chunks, threshold=95.0):
    """A question copied out of a chunk measures string matching, not retrieval."""
    return [r["id"] for r in rows
            if any(fuzz.partial_ratio(r["question"], c) >= threshold for c in chunks)]

# tests/test_dataset.py
def test_every_slice_is_populated():
    assert {r["slice"] for r in load_golden()} == SLICES

def test_abstain_slice_is_big_enough():
    rows = load_golden()
    assert sum(r["expects_abstention"] for r in rows) >= 5

def test_no_near_duplicates():
    assert near_duplicates(load_golden()) == []`,
    },
    {
      id: "p-evals-e2",
      title: "A judged run, and a harness you can unit-test",
      repo: "phase3-evals/02-llm-judge",
      rung: "faded",
      proves: "implement",
      task: "Score the golden set with RAGAS `Faithfulness` and `ContextRecall` against a pinned local judge. The trick: structure it so the *harness* — row building, aggregation, slice breakdown, gate logic — is fully covered by offline tests, and only the judge call itself needs a model.",
      assesses: ["p-evals-o2"],
      needs: ["p1-o1"],
      solution: [
        "Put the judge behind a small `Judge` protocol. Offline tests inject a deterministic fake; the real RAGAS judge lives behind the `integration` group.",
        "Aggregate **per slice** as well as overall, and print the slice table — an average is where a broken abstain path hides.",
        "Record the judge model, temperature and RAGAS version in the results file. A score without its instrument is not a measurement.",
      ],
      code: `# src/harness.py — the judge is injected, so the harness is testable offline
from typing import Protocol

class Judge(Protocol):
    def faithfulness(self, q: str, answer: str, contexts: list[str]) -> float: ...
    def context_recall(self, q: str, contexts: list[str], reference: str) -> float: ...

def run(rows, pipeline, judge: Judge) -> dict:
    scored = []
    for row in rows:
        answer, contexts = pipeline(row["question"])
        if row["expects_abstention"]:                 # judge-free, and the
            scored.append({**row, "faithfulness": float(abstained(answer)),
                           "context_recall": 1.0})    # most important slice
            continue
        scored.append({**row,
            "faithfulness": judge.faithfulness(row["question"], answer, contexts),
            "context_recall": judge.context_recall(row["question"], contexts,
                                                   row["ground_truth"])})
    return {"overall": mean_of(scored), "by_slice": grouped_means(scored)}

# tests/test_harness.py (offline, no model)
def test_abstention_row_passes_when_system_abstains():
    out = run([ABSTAIN_ROW], pipeline=lambda q: ("Not in the docs.", []),
              judge=FakeJudge(0.0))
    assert out["overall"]["faithfulness"] == 1.0`,
    },
    {
      id: "p-evals-e3",
      title: "Calibrate the judge against your own labels",
      repo: "phase3-evals/03-judge-calibration",
      rung: "faded",
      proves: "integrate",
      task: "Hand-label 50 judged rows pass/fail yourself, then measure agreement and Cohen’s κ against the judge. Sweep the threshold for the best κ, read every disagreement, and write down the κ you will quote alongside your scores.",
      assesses: ["p-evals-o3"],
      solution: [
        "Report κ, not accuracy. With a 90% pass rate, accuracy makes a rubber-stamp judge look excellent.",
        "The disagreements are the deliverable: each one is a bad rubric, a bad label, or a question too ambiguous to belong in the golden set.",
        "Set your CI regression tolerance *from* the calibration — if the judge disagrees with you on 8% of rows, a 2-point move is noise.",
      ],
      code: `# src/calibration.py
from sklearn.metrics import cohen_kappa_score

LABELS = ["pass", "fail"]

def calibrate(rows) -> dict:
    human = [r["human"] for r in rows]
    judge = [r["judge"] for r in rows]
    return {
        "n": len(rows),
        "agreement": sum(h == j for h, j in zip(human, judge)) / len(rows),
        "kappa": cohen_kappa_score(human, judge, labels=LABELS),
        "disagreements": [r["id"] for r in rows if r["human"] != r["judge"]],
    }

def best_threshold(rows) -> tuple[float, float]:
    """Pick the cut point from the data instead of defaulting to 0.5."""
    return max(
        ((cohen_kappa_score([r["human"] for r in rows],
                            ["pass" if r["score"] >= t else "fail" for r in rows],
                            labels=LABELS), t)
         for t in (i / 20 for i in range(1, 20))),
    )

# tests/test_calibration.py — all offline: fixtures, not models
def test_rubber_stamp_judge_has_near_zero_kappa():
    rows = [{"id": i, "human": "pass" if i else "fail", "judge": "pass"}
            for i in range(20)]
    assert calibrate(rows)["agreement"] > 0.9
    assert calibrate(rows)["kappa"] < 0.1        # agreement lied; kappa didn't`,
    },
    {
      id: "p-evals-e4",
      title: "The gate that blocks the merge",
      repo: "phase3-evals/04-ci-regression-gate",
      rung: "faded",
      proves: "operate",
      task: "Commit a `baseline.json`, then build `make gate`: it fails on an absolute-bar breach, on a per-slice regression beyond tolerance, and on a stale baseline. Wire it into a GitHub Actions workflow with the fast tier on every PR and the judged tier nightly.",
      assesses: ["p-evals-o5"],
      solution: [
        "Gate on slices, not just the overall mean — that is where a collapsed abstain path hides.",
        "Re-baselining must be an explicit, reviewed commit. A gate that updates its own baseline is a gate that never fails.",
        "Print a diff table, not a stack trace. The failure message is a code-review artifact; make it readable.",
      ],
      code: `# Makefile
gate:            ## fail the build on a regression (no model needed)
	uv run python -m src.gate evals/results.json evals/baseline.json

# .github/workflows/evals.yml
on: [pull_request, schedule]
jobs:
  fast:                        # every PR: dataset tests + trajectory + gate logic
    steps:
      - run: make check
      - run: make gate
  judged:                      # nightly only: costs tokens / needs a judge
    if: github.event_name == 'schedule'
    steps:
      - run: make test-integration

# src/gate.py prints the receipt, then exits 1
# metric            base    now     delta
# faithfulness      0.91    0.88    -0.03   ok (within tolerance)
# unanswerable      1.00    0.57    -0.43   FAIL  <- the abstain path broke`,
    },
    {
      id: "p-evals-e5",
      title: "Blank editor: calibrate a judge with no library and no scaffold",
      rung: "independent",
      proves: "integrate",
      task: "Empty directory, no RAGAS, no scikit-learn. Take 30 answers from anything you have built and label them pass or fail yourself, first, before the judge sees them — that ordering is not optional. Then write a judge prompt, run it, and compute raw agreement and Cohen’s κ from the confusion matrix with arithmetic you wrote. Print both, plus the base rate of your own labels. Finish by writing down the threshold you would gate on and why.",
      assesses: ["p-evals-o2", "p-evals-o3"],
      needs: ["p1-o4"],
      solution: [
        "You labeled before you ran the judge. Labeling afterwards means anchoring on its verdict, which quietly manufactures the agreement you were trying to measure — and no library can save you from it, which is why this task is hand-rolled.",
        "Your κ implementation divides observed-minus-expected agreement by one-minus-expected, and you can say out loud what the expected term represents. Writing those four cells and that fraction yourself is the difference between quoting κ and understanding why raw agreement lied to you.",
        "You printed your own base rate next to the score. A 90% agreement on a set where 88% of rows pass is a number you now know how to distrust.",
        "Your judge prompt asks for a verdict *and* a reason, with the reason first. Reversed, the model commits to a verdict and then rationalises it — the same order-of-operations bug as labeling after the judge.",
        "The threshold you chose comes with a sentence about your own disagreement rate. You cannot detect a regression smaller than the noise between you and your judge, and knowing your own noise floor is the whole point of the afternoon.",
      ],
    },
  ],
  checkpoint: [
    {
      id: "p-evals-q1",
      q: "Your faithfulness score is 0.93 and users are complaining. Where do you look first?",
      a: "At the golden set, not the system. The usual cause is a dataset that can’t express the failure — most often no unanswerable rows (so the abstain path is untested) or questions generated from the indexed chunks (so every question is answerable by construction and phrased like its own source). Then check the per-slice breakdown: a high average routinely hides one collapsed slice.",
      demands: ["evidence", "failure-modes"],
    },
    {
      id: "p-evals-q2",
      q: "The judge agrees with your labels 92% of the time. Is it good enough to gate merges?",
      a: "Unknown from that number alone. If 92% of rows are passes, a judge that always says “pass” scores the same 92%. Report Cohen’s κ, which corrects for chance agreement: κ near 0 means a rubber stamp, and roughly 0.6+ is where gating merges starts to be defensible. κ also sets your regression tolerance — you cannot detect a delta smaller than your judge’s disagreement with you.",
      demands: ["constraints", "evidence", "failure-modes"],
    },
    {
      id: "p-evals-q3",
      q: "Which parts of an eval suite should need no LLM at all?",
      a: "Dataset integrity (slices populated, no near-duplicates, no leakage), retrieval metrics computed from `supporting_doc_ids`, abstention checks, all trajectory metrics (tool choice, arguments, step count), aggregation and the gate logic itself. Everything there is deterministic, free, offline, and belongs in the per-PR tier — the judge is reserved for what genuinely requires reading meaning.",
      demands: ["alternatives", "constraints"],
    },
    {
      id: "p-evals-q4",
      q: "Why gate on both absolute bars and regression deltas?",
      a: "A bar alone permits slow rot: every PR passes at 0.86 while you slide down from 0.94. A delta alone permits a permanently broken system as long as it doesn’t get worse. Together they catch both. The tolerance on the delta has to exceed the noise you measured during calibration, or CI cries wolf and people start routing around it.",
      demands: ["alternatives", "constraints", "failure-modes"],
    },
    {
      id: "p-evals-q5",
      q: "An agent answered the user’s question correctly. Why might that still be a failing trace?",
      a: "Because the trajectory can be wrong while the final message is right: it called a destructive tool, passed the wrong argument to a gated tool, acted without the required approval, or burned six tool calls on a one-call task. Those are the failures that page you at 3 a.m., and they are all checkable offline against reference tool calls.",
      demands: ["evidence", "failure-modes"],
    },
  ],
  workshop: {
    id: "w-evals",
    title: "Workshop · Prove the RAG service works",
    subtitle:
      "Put the Workshop-2 service on trial: golden set, calibrated judge, and a CI gate that blocks your own merges.",
    repo: "workshops/assistant",
    proves: "operate",
    assesses: ["p-evals-o1", "p-evals-o2", "p-evals-o3", "p-evals-o4", "p-evals-o5"],
    needs: ["p2-o1", "p2-o3"],
    blocks: [
      {
        kind: "p",
        text: "The previous workshop left you with a RAG service that answers questions. This one asks the only question that matters next: **how do you know it’s any good?** You will build the eval layer of the assistant — a sliced golden set over its corpus, an injectable judge, a calibration report with your own labels, and a gate that fails the build when a slice regresses.",
      },
      {
        kind: "p",
        text: "Every later workshop plugs into this layer instead of re-inventing it: the memory workshop adds recall rows, the hardening workshop adds red-team rows, the deploy workshop wires the gate into the pipeline.",
      },
      {
        kind: "callout",
        tone: "tip",
        title: "Everything here runs offline",
        text: "The suite is designed so the judge is the *only* component that needs a model, and it sits behind a `Judge` protocol with a deterministic fake for tests. That is not a course convenience — it is how you get an eval gate that runs on every PR in under a minute without a budget conversation.",
      },
      {
        kind: "flow",
        title: "The eval layer you’re adding",
        nodes: [
          { label: "golden.jsonl", sub: "5 slices, provenance, abstain rows" },
          { label: "Dataset tests", sub: "dupes · leakage · slice balance" },
          { label: "Harness", sub: "run → per-slice scores" },
          { label: "Calibration", sub: "your labels vs the judge, κ" },
          { label: "Gate", sub: "bars + baseline deltas → exit 1" },
        ],
      },
      {
        kind: "code",
        title: "The seam you implement",
        code: `# before/src/assistant/evals.py
class Judge(Protocol):
    """The only component allowed to need a model."""
    def verdict(self, question: str, answer: str, contexts: list[str]) -> float: ...

def run_suite(rows: list[GoldenRow], answer_fn, judge: Judge) -> SuiteResult:
    # TODO: score every row; abstention rows are judged WITHOUT the judge
    # TODO: aggregate overall AND per slice
    ...

def gate(result: SuiteResult, baseline: dict[str, float],
         bars: dict[str, float], tolerance: float) -> list[str]:
    # TODO: absolute-bar breaches + per-slice regressions beyond tolerance
    # TODO: return human-readable reasons; empty list means the merge may land
    ...`,
      },
      {
        kind: "callout",
        tone: "warn",
        title: "You are allowed to fail your own gate",
        text: "If your honest golden set puts the Workshop-2 service below the bar, **do not move the bar**. Write the number down, fix the retrieval, and watch the number move. The whole point of this phase is having a metric with enough integrity to tell you bad news.",
      },
    ],
    deliverables: [
      {
        id: "w-evals-d1",
        text: "`golden.jsonl` has **all five slices** populated, at least 5 unanswerable rows, and provenance on every row",
        tier: "minimum",
      },
      {
        id: "w-evals-d2",
        text: "Dataset tests fail on a planted near-duplicate and on a question copied verbatim out of a chunk",
        tier: "full",
      },
      {
        id: "w-evals-d3",
        text: "`make eval` prints an **overall + per-slice** table; the abstention slice is scored without a judge",
        tier: "minimum",
      },
      {
        id: "w-evals-d4",
        text: "A calibration report over ≥30 hand-labeled rows quotes **agreement and Cohen’s κ**, and your tolerance is derived from it",
        tier: "full",
      },
      {
        id: "w-evals-d5",
        text: "`make gate` exits non-zero on an absolute-bar breach **and** on a per-slice regression against the committed `baseline.json`",
        tier: "full",
      },
      {
        id: "w-evals-d6",
        text: "The fast tier (dataset + harness + gate + trajectory checks) runs with **no model and no network**, in under a minute",
        tier: "full",
      },
    ],
    stretch: [
      "Calibrate the free local judge against a hosted one on the same rows and write the one-paragraph decision: which judge gates your merges, and why.",
      "Add a trajectory check with `ToolCallAccuracy` asserting that a gated tool never fires without approval — then keep it green through the hardening workshop.",
      "Add a sampling script: pull the lowest-confidence traces from a log file, print them for review, and append accepted ones as new golden rows with provenance.",
    ],
  },
  resources: [
    { label: "RAGAS docs (metrics & collections API)", url: "https://docs.ragas.io" },
    {
      label: "OpenAI Evals — cookbook & harness patterns",
      url: "https://cookbook.openai.com/examples/evaluation/getting_started_with_openai_evals",
    },
    {
      label: "Anthropic — creating strong empirical evaluations",
      url: "https://docs.anthropic.com/en/docs/test-and-evaluate/develop-tests",
    },
    {
      label: "“Judging LLM-as-a-Judge” (MT-Bench / Chatbot Arena)",
      url: "https://arxiv.org/abs/2306.05685",
    },
    {
      label: "scikit-learn — Cohen’s kappa",
      url: "https://scikit-learn.org/stable/modules/generated/sklearn.metrics.cohen_kappa_score.html",
    },
    { label: "Langfuse — datasets, scores & CI", url: "https://langfuse.com/docs/evaluation" },
    { label: "Arize Phoenix — online evals & sampling", url: "https://phoenix.arize.com" },
  ],
};
