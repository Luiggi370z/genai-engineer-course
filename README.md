# The GenAI Engineer Workbook

**An 18-week workbook that takes a working software engineer to shipping GenAI systems
they can defend — evaluated, guarded, deployed, and measured.**

Most AI courses show you a system being built. You watch someone wire up a RAG demo, it
answers a question, and the video ends. Then an interviewer asks how you know it works,
what happens when a user tells your agent to ignore its instructions, or what it costs
per thousand queries — and the demo has taught you nothing that helps.

This is a workbook instead. You build one assistant across nine phases and nine
workshops, and each phase adds the thing the demos skip: a golden set and a judge you
calibrated yourself, a leash on the agent that lives in code rather than in the prompt,
a memory you can invalidate, a red-team suite in CI, a deploy with a rollback path, and
a P99 budget you can defend. You finish with **one system you can explain end to end**,
and numbers to quote about it.

---

## Before you start: what you need

**Skills.** You should already write Python comfortably (type hints, `async`/`await`,
Pydantic, pytest) and be able to read a stack trace without flinching. You should know
git, HTTP and JSON, and have met Docker. This is **not** a first programming course, and
it is not an introduction to Python — it assumes you can build software and teaches you
to build *this kind* of software.

You do not need a machine-learning background. Vectors, cosine similarity and a feel for
probability are plenty; there is no maths derivation anywhere in here.

**Hardware.** A **16 GB machine runs the entire course locally**, models included. More
RAM unlocks stronger models but changes nothing you learn — and if you have less, or no
GPU, every lesson runs against a hosted budget tier by changing one `base_url`. Phase 1
carries the full sizing table.

The one exception worth naming: the Phase 3 eval judge is nicer on 32 GB, because a
bigger local model makes a better judge. It is deliberately swappable, and any capable
model works.

**Money.** None. Every lesson's fast test tier runs **offline with zero API keys** —
that is a design constraint of this course, not an accident. Hosted providers are
optional everywhere, for when you want to see the difference.

**Software.** Python 3.11+, [uv](https://docs.astral.sh/uv/),
[Ollama](https://ollama.com), and Docker for the Phase 8 deployment lessons.

---

## Start here

```bash
# 1. Open the course. It is one self-contained file — no server, no build, no network.
open src/course.html

# 2. Install the toolchain and pull the models the course uses.
curl -LsSf https://astral.sh/uv/install.sh | sh
ollama pull qwen3.5:8b        # chat + tool calling
ollama pull nomic-embed-text  # embeddings

# 3. Do the first lesson.
cd src/phase1-foundations/01-universal-client/before
make setup && make test       # red: the TODOs are yours to fill in
$EDITOR src/client.py
make check                    # green: lint, types and tests
```

Two more models (`qwen3-coder:30b` for the Phase 3 judge, `llama-guard3:8b` for the
Phase 6 guardrails) are worth pulling when you reach those phases rather than now.

Your progress in `course.html` is saved in the browser's `localStorage`, so tick things
off as you go — but keep in mind it lives in that one browser on that one machine.

---

## How the lessons work

Every exercise ships twice. **`before/`** is a runnable scaffold with the judgement
removed and `TODO`s where your work goes; its tests fail on purpose, and turning them
green is the exercise. **`after/`** is a working reference — open it when you are stuck,
not before, because reading a solution feels exactly like understanding one.

That pairing is the whole pedagogical spine: each phase moves you along a **worked →
faded → independent** ladder, and every phase ends with at least one task that hands you
a blank editor and no scaffold at all. If you only ever fill in blanks, you will learn to
recognise good code rather than write it, which is the failure mode this course is built
to avoid.

Tests come in two tiers: `make test` is fast, offline and deterministic, and
`make test-integration` runs the same code against real models. Full mechanics — the
`make` targets, the library stack, version pinning — are in
[`src/README.md`](src/README.md).

---

## The nine phases

Each phase runs about two weeks and ends in a workshop that adds a layer to the same
assistant. Workshops 1 and 9 bookend it: the tool you measure with, and the loop that
turns everything into offers.

| # | Phase | You build | Afterwards you can prove |
|:-:|-------|-----------|--------------------------|
| 1 | Speak Fluent LLM | One client across every provider; a RAG pipeline by hand | You bill from `usage`, not estimates, and every later stage has a name you know |
| 2 | Retrieval That Actually Works | Hybrid search + reranker, behind an offline gate | Retrieval choices backed by numbers, and stage-by-stage debugging under pressure |
| 3 | Prove It Works: Evals & Judges | Golden set, calibrated judge, CI merge gate | "It works" — with a κ against your own labels and a gate that blocks your merges |
| 4 | Agents on a Leash | The reason–act–observe loop from scratch, then frameworks | An agent contained in code: step caps, deadlines, approval on anything irreversible |
| 5 | Agents That Remember & Collaborate | Memory with provenance and TTL; a delegating crew | A fact recalled, cited, and correctly forgotten — with the cost of delegation measured |
| 6 | Whiteboard It & Defend It | The 8-step design script; layered guardrails | A system designed out loud, and an injection that lands but cannot fire a gated tool |
| 7 | MCP: The Universal Tool Port | Your own MCP server, consumed by your assistant | Tools that any agent can use, with the right auth for each deployment |
| 8 | Run It in Production | Containers, CI, OpenTelemetry, cache and routing | A deployed stack, gated on evals and red-team, defended on P99 rather than an average |
| 9 | The GenAI Mindset | Drill deck, metric-mined resume, funnel tracker | Every claim traced to a file you wrote, and a job search you can debug |

The full lesson-by-lesson map is in [`src/README.md`](src/README.md), and there is an
electives shelf in the app — fine-tuning, multimodal, GraphRAG, GPU serving — for topics
you should only pick up once they appear in three job descriptions you actually want.

---

## Gates, not dates

The week numbers are a shape, not a schedule. What decides whether you move on is the
milestone at the end of each phase, and the milestones are written as things that either
happen or do not: the service answers with citations and abstains when it cannot;
faithfulness clears 0.85 on a 50-question golden set; no landed injection fires a gated
tool.

Miss one and the honest move is to stay — the fix-it playbook for each is part of the
syllabus rather than an appendix. The workbook tracks all of this for you; the dashboard
in `course.html` is the checklist.

Reading the phase takes minutes and the app tells you how many. Doing it takes the
fortnight. Those are very different numbers and the course is careful never to blur them.

---

## Where to get unstuck

1. **Re-read the failing test.** The `before/` tests are written to describe the shape of
   the answer, not just to fail.
2. **Check the phase's `VERIFIED.md`.** Each phase carries a dated stamp saying when its
   lessons last passed and what library versions they were built against. GenAI
   dependencies break fast; if that date is old, expect drift, and upgrade one dependency
   at a time.
3. **Open `after/`.** It is a reference, not a cheat — but read it, then close it and
   write your own.
4. **Run `./src/verify-lessons.sh`** if something looks broken in the repo rather than in
   your code. It checks every lesson in the course and tells you which one is unhappy.

---

## What is in this repo

- **[`src/`](src/README.md)** — the companion code: every `before/`+`after/` lesson pair,
  the nine workshop briefs, and `course.html` itself. This is the part you work in.
- **[`app/`](app/README.md)** — the source of the course app. Only interesting if you
  want to change the course; students never need it. React and TypeScript, building to
  that single HTML file, with three gates (alignment, integrity, density) that content
  has to pass before it can ship.

## License

MIT — use it, fork it, teach from it.
