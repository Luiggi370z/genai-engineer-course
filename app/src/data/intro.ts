// Generated from the shipped course bundle by scripts/extract-data.mjs.
// Edit freely from here on — this file is the source of truth for the content.

import type { Milestone, Myth, Prerequisite } from "./types";

export const prerequisites: Prerequisite[] = [
  {
    id: "pre-1",
    text: "**Python (comfortable)** — type hints, async/await, Pydantic, uv or poetry, pytest",
  },
  {
    id: "pre-2",
    text: "**APIs & HTTP** — verbs, status codes, auth (API keys, OAuth2), JSON, SSE/streaming, retry with backoff",
  },
  { id: "pre-3", text: "**Git/GitHub** — branching, PRs, code review" },
  {
    id: "pre-4",
    text: "**Docker basics** — Dockerfile, docker compose, multi-stage builds",
  },
  {
    id: "pre-5",
    text: "**A cloud** — any of AWS/GCP/Azure: compute, object storage, secrets, a managed Postgres",
  },
  {
    id: "pre-6",
    text: "**SQL** — joins, indexes, basic tuning (pgvector will feel familiar)",
  },
  {
    id: "pre-7",
    text: "**Design patterns** — adapter/strategy and dependency injection carry this whole course",
  },
  {
    id: "pre-8",
    text: "**Optional hardware** — any 16GB+ machine runs the local-model lessons; more RAM unlocks stronger models (sizing table in Phase 1). No GPU at all? Hosted budget tiers cover everything.",
  },
  {
    id: "pre-9",
    text: "**Light math** — vectors, cosine similarity, probability intuition. No PhD required, promise",
  },
];

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
