// Generated from the shipped course bundle by scripts/extract-data.mjs.
// Edit freely from here on — this file is the source of truth for the content.

import type { Milestone, Myth, OutOfScope, Prerequisite } from "./types";

/**
 * Two groups, because an undifferentiated list of nine is read as nine gates.
 *
 * `required` is the honest floor: without these you will be learning two things
 * at once and blaming the wrong one. Everything in `helpful` is either taught
 * here (OAuth 2.1 and PKCE are Phase 7's subject, not an entry fee) or has a
 * stated way around it, so a reader who has never provisioned a cloud can still
 * finish. Both READMEs restate this list inside a canonical block and
 * `pnpm check-claims` fails when a copy drifts.
 */
export const prerequisites: Prerequisite[] = [
  {
    id: "pre-1",
    need: "required",
    text: "**Python (comfortable)** — type hints, async/await, Pydantic, uv or poetry, pytest",
  },
  {
    id: "pre-2",
    need: "required",
    text: "**APIs & HTTP** — verbs, status codes, API-key auth, JSON, SSE/streaming, retry with backoff",
  },
  { id: "pre-3", need: "required", text: "**Git/GitHub** — branching, PRs, code review" },
  {
    id: "pre-4",
    need: "required",
    text: "**Docker basics** — Dockerfile, docker compose, multi-stage builds",
  },
  {
    id: "pre-5",
    need: "helpful",
    text: "**A cloud** — any of AWS/GCP/Azure. Phase 8 deploys with compose on one box; a cloud makes the last mile familiar rather than possible",
  },
  {
    id: "pre-6",
    need: "helpful",
    text: "**SQL** — joins and indexes make pgvector feel familiar, but every query the course writes is shown in full",
  },
  {
    id: "pre-7",
    need: "helpful",
    text: "**Design patterns** — adapter/strategy and dependency injection carry this whole course; you can also just read them off the lessons that use them",
  },
  {
    id: "pre-8",
    need: "helpful",
    text: "**Hardware** — any 16GB+ machine runs the local-model lessons; more RAM unlocks stronger models (sizing table in Phase 1). No GPU at all? Hosted budget tiers cover everything.",
  },
  {
    id: "pre-9",
    need: "helpful",
    text: "**Light math** — vectors, cosine similarity, probability intuition. No PhD required, promise",
  },
];

/** The prerequisite list as the READMEs carry it, grouped by need. */
export function prerequisiteSummaryMarkdown(): string {
  const bullets = (need: Prerequisite["need"]) =>
    prerequisites.filter((item) => item.need === need).map((item) => `- ${item.text}`);
  return [
    "**Required — assumed on day one.**",
    "",
    ...bullets("required"),
    "",
    "**Helpful, not required** — each is either taught here or has a stated way around it.",
    "",
    ...bullets("helpful"),
  ].join("\n");
}

export const myths: Myth[] = [
  {
    title: "The expensive-router myth",
    text: "The original chart says to route with the priciest model and do the work with the cheapest. In practice it’s usually the reverse: **triage with a cheap, fast model** (even a local 8B) and escalate only the hard cases — or put the strong model on **planning** and let cheap workers execute. Pick model strength per task, per node.",
  },
  {
    title: "Plain vector search is a 2023 answer",
    text: "Embedding-only retrieval whiffs on exact things — invoice numbers, statutes, error codes. **Hybrid search (keyword + vectors) plus a reranker is today’s starting line**, not a bonus round.",
  },
  {
    title: "Projects > certificates — with a catch",
    text: "Three shipped projects really do outweigh a wall of certificates — **but only if they carry numbers**: eval scores, latency, cost, a one-command deploy. A demo without metrics is just a certificate with extra steps.",
  },
  {
    title: "What the chart forgot entirely",
    text: "Security and **guardrails** (prompt injection is OWASP’s #1 LLM risk), an **evaluation habit** (golden sets in CI), **local models** (Ollama/MLX), and knowing when to fine-tune vs retrieve. All four are woven through this course.",
  },
];

/**
 * The scope, stated as an exclusion list. A syllabus that only says what it
 * covers leaves the reader to infer the boundary from an absence, which is how
 * someone finishes nine phases still believing they were taught how models are
 * made. This course is about *building systems on top of* models; none of the
 * below is a prerequisite for that, and all of it is a prerequisite for a
 * different job.
 */
export const outOfScope: OutOfScope[] = [
  {
    topic: "Transformer mathematics and model architecture",
    why: "You will use attention every day and never implement it. The course treats a model as a component with a latency, a price and a failure mode — which is the correct abstraction for building on one, and the wrong one for changing one.",
    next: "Karpathy’s *Let’s build GPT* and *The Illustrated Transformer*, then Bishop or the Goodfellow book if you want the maths underneath.",
  },
  {
    topic: "Pretraining and distributed training",
    why: "Nothing here trains a base model. Data pipelines at the trillion-token scale, sharding strategies, and the systems work of keeping a thousand GPUs busy are a specialty with its own hiring loop.",
    next: "The Llama and OLMo technical reports, then the *Ultra-Scale Playbook* for the parallelism.",
  },
  {
    topic: "Fine-tuning and alignment research",
    why: "The electives shelf covers when to fine-tune and how LoRA fits a workflow. It does not cover RLHF, DPO, reward modelling or the research on what alignment even means — and the honest default in this course is that retrieval and prompting solve most of what people reach for fine-tuning to fix.",
    next: "The InstructGPT and DPO papers, then the Hugging Face alignment handbook for the practice.",
  },
  {
    topic: "GPU inference kernels, quantization and serving at scale",
    why: "You will run local models through Ollama and reason about tokens per second and RAM. You will not write CUDA, implement paged attention, or tune a vLLM cluster. The elective goes as far as *running* vLLM, not operating it under load.",
    next: "The vLLM and FlashAttention papers, and the llama.cpp quantization docs for what the GGUF suffixes actually mean.",
  },
  {
    topic: "Multimodal depth",
    why: "Vision and audio appear as electives and as capabilities you call. Training a VLM, building a speech pipeline, or the evaluation problems specific to generated images are each their own course.",
    next: "The CLIP and Whisper papers; for production voice, start from latency budgets rather than model choice.",
  },
  {
    topic: "Research methodology",
    why: "This course teaches you to measure a system you built. It does not teach you to design a study, choose a baseline that survives review, or reason about statistical significance across seeds — the skills that separate an engineer’s benchmark from a paper’s.",
    next: "*How to Read a Paper* (Keshav), then reproduce one result end to end; the gap between the paper and your rerun is the lesson.",
  },
];

export const milestones: Milestone[] = [
  {
    stage: "Foundations + retrieval (phases 1–2, Workshop 2)",
    bar: "A RAG service that runs from one command, answers with citations, and abstains when the corpus can’t support an answer. Can’t hit it? Stay — the fix-it playbook is the syllabus.",
  },
  {
    stage: "Proof (phase 3, Workshop 3)",
    bar: "Faithfulness ≥ 0.85 and context recall ≥ 0.80 on a 50-question golden set, scored by a judge you calibrated against your own labels, gating merges in CI. A number you can’t defend is not a number.",
  },
  {
    stage: "Agents (phase 4, Workshop 4)",
    bar: "Explain the loop cold, build a tool properly, and ship a personal assistant with HITL on every irreversible action. Justify your framework choice out loud.",
  },
  {
    stage: "Memory + collaboration (phase 5, Workshop 5)",
    bar: "The assistant recalls a fact from a previous session, cites where it learned it, drops a fact you corrected — and a tiered crew reports its cost next to the quality score, not instead of it.",
  },
  {
    stage: "Design + defense (phase 6, Workshop 6)",
    bar: "Run the 8-step design script; name the attack families and their defenses; harden the assistant so no landed injection can fire a gated tool, proven by a red-team suite in CI.",
  },
  {
    stage: "MCP + deployment (phases 7–8, Workshops 7–8)",
    bar: "Your own MCP server, consumed by your assistant via discovery, with correct auth; the whole stack deployed from one command, CI-gated on evals + red-team, observable.",
  },
  {
    stage: "Job hunt (phase 9)",
    bar: "Every resume bullet carries a number mined from a workshop; funnel tracker live; daily reps running.",
  },
  {
    stage: "Electives — only on demand",
    bar: "Fine-tuning mechanics, multimodal, voice, scaled GPU serving (vLLM), GraphRAG: add one only when it shows up in ≥3 target job descriptions.",
  },
];
