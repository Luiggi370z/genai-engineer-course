/**
 * The numbers that go stale, in one place, each with the page it came from and
 * the day someone looked.
 *
 * Vendor prices, hardware tiers and model tags were previously written out
 * wherever they were needed — the sizing table in Phase 1, a shorter version in
 * the root README, a shorter one again in the release README, and the model tags
 * in forty-odd Python defaults. That is four copies of a fact with a shelf life
 * of about a quarter, and the audit found them already disagreeing: the eval
 * judge was `qwen3-coder:30b` in the course text and `qwen3.6:27b` in the code
 * that ran it.
 *
 * So: one table, rendered into the workbook, checked against the READMEs and the
 * lesson code by `scripts/check-claims.mjs`. Updating a price is a one-line edit
 * here, and the gate tells you every other place that now disagrees.
 *
 * Two rules for anything added to this file:
 *
 *   1. **A source or it does not go in.** Not "I read it somewhere" — a URL a
 *      reader can open and check against. A number without one is a rumour with
 *      a decimal point.
 *   2. **A `verifiedOn` date, and it is the day you actually looked**, not the
 *      day you typed the number in from memory. The date is what lets a reader
 *      six months from now discount the figure appropriately, which is more
 *      useful than a number that is quietly wrong.
 */

export interface Source {
  label: string;
  url: string;
}

/** A claim with a shelf life: what it says, where it came from, when it was checked. */
export interface Sourced {
  source: Source;
  /** ISO `YYYY-MM-DD`. Checked to be a real date, and not in the future. */
  verifiedOn: string;
}

// ---------------------------------------------------------------------------
// Hosted model prices
// ---------------------------------------------------------------------------

export interface VendorRow extends Sourced {
  vendor: string;
  /** The expensive one. Format: `Name · $in/$out` per million tokens. */
  flagship: string;
  /** The one you actually use daily. */
  daily: string;
  /** The routing-and-grunt-work tier. */
  budget: string;
}

export const VENDORS: VendorRow[] = [
  {
    vendor: "Anthropic",
    flagship: "Opus 4.8 · $5/$25 (Fable 5 above it)",
    daily: "Sonnet 4.6 · $3/$15",
    budget: "Haiku 4.5 · $1/$5",
    source: { label: "Anthropic pricing", url: "https://www.anthropic.com/pricing" },
    verifiedOn: "2026-08-01",
  },
  {
    vendor: "OpenAI",
    flagship: "GPT-5.5 · $5/$30",
    daily: "GPT-5.2 · $1.75/$14",
    budget: "GPT-5.4 mini/nano",
    source: { label: "OpenAI API pricing", url: "https://openai.com/api/pricing/" },
    verifiedOn: "2026-08-01",
  },
  {
    vendor: "Google",
    flagship: "Gemini 3.1 Pro · $2/$12 (3.5 Pro not GA yet)",
    daily: "Gemini 3.5 Flash · $1.50/$9",
    budget: "3.1 Flash-Lite · $0.25/$1.50",
    source: { label: "Gemini API pricing", url: "https://ai.google.dev/gemini-api/docs/pricing" },
    verifiedOn: "2026-08-01",
  },
];

/**
 * The prices the lesson code prices tokens with, in dollars per million.
 *
 * Separate from `VENDORS` because these are consumed by a machine and compared
 * against the `PRICE` dicts in `src/`, where a display string like "$3/$15"
 * would have to be parsed back into numbers by the very gate meant to stop
 * numbers drifting.
 */
export const TOKEN_PRICES: Record<string, { in: number; out: number }> = {
  "claude-opus-4-8": { in: 5.0, out: 25.0 },
  "claude-sonnet-4-6": { in: 3.0, out: 15.0 },
  "claude-haiku-4-5": { in: 1.0, out: 5.0 },
  "gpt-5.5": { in: 5.0, out: 30.0 },
  "gpt-5.2": { in: 1.75, out: 14.0 },
  "gpt-5.4-mini": { in: 0.25, out: 2.0 },
};

// ---------------------------------------------------------------------------
// Hardware
// ---------------------------------------------------------------------------

export interface HardwareTier {
  /** What the student has. The join key for the shorter README table. */
  ram: string;
  /** Ollama tags that run comfortably there. */
  tags: string;
  /** What having them lets you do in this course. */
  unlocks: string;
  /**
   * The README wording for this tier, when it is one of the four the READMEs
   * carry. Present means "include me in the short table".
   *
   * The summary is a subset with its own phrasing, not a second set of facts —
   * which is the only reason two tables are allowed to exist at all.
   * `check-claims.mjs` rebuilds the README table from these fields, so the short
   * one cannot drift from the long one the way it had before this file existed.
   */
  summary?: { runs: string; know: string };
}

export const HARDWARE_VERIFIED: Sourced = {
  source: { label: "Ollama model library", url: "https://ollama.com/library" },
  verifiedOn: "2026-08-01",
};

export const HARDWARE: HardwareTier[] = [
  {
    // First row, and it is not a compromise. Every lesson's fast tier runs with
    // no model at all, which is the single most reassuring fact about this
    // course's hardware story and was previously only in the README.
    ram: "Any machine",
    tags: "No models — every lesson's fast test suite",
    unlocks: "`make test` everywhere: offline, deterministic, no keys",
    summary: {
      runs: "Every lesson's fast test suite (`make test`)",
      know: "Offline, deterministic, no models, no keys — the whole course can be *completed* here",
    },
  },
  {
    ram: "~8 GB",
    tags: "gemma4:e2b · nomic-embed-text",
    unlocks: "Light chat, embeddings, learning the APIs",
  },
  {
    ram: "16 GB",
    tags: "qwen3.5:9b · gemma4:e4b · gpt-oss:20b",
    unlocks: "The whole course locally: routing, agents, guard models",
    summary: {
      runs: "The course's working models locally: `qwen3.5:9b`, `gemma4:e4b`, embeddings, guard models",
      know: "The recommended local path. The 30B eval judge does **not** fit here — swap in a smaller judge or a hosted one",
    },
  },
  {
    ram: "24 GB (or a 24GB GPU)",
    tags: "+ qwen3.6:27b · gemma4:31b (Q4)",
    unlocks: "Best local coding + generalist quality on consumer hardware",
  },
  {
    ram: "32–64 GB",
    tags: "+ qwen3-coder:30b (the MLX-on-Mac favorite)",
    unlocks: "Agentic coding, bigger contexts, a free local eval judge",
    summary: {
      runs: "+ `qwen3-coder:30b` as a free local Phase 3 judge",
      know: "The comfortable path; bigger judges are measurably better",
    },
  },
  {
    ram: "64 GB+ / 80GB GPU",
    tags: "+ qwen3-coder-next · gpt-oss:120b",
    unlocks: "Open frontier-class reasoning and coding",
  },
  {
    ram: "No GPU / older laptop",
    tags: "Hosted budget tiers or Ollama cloud models",
    unlocks: "Same code, same lessons — just a different base_url",
    summary: {
      runs: "Everything, against a hosted budget tier by changing one `base_url`",
      know: "Needs an account, an API key, and network; costs real (small) money",
    },
  },
];

// ---------------------------------------------------------------------------
// The models the course actually pulls
// ---------------------------------------------------------------------------

export type ModelRole = "chat" | "embed" | "rerank" | "judge" | "guard";

export interface CourseModel {
  role: ModelRole;
  /** The exact tag. This string is what the gate looks for in `src/`. */
  tag: string;
  /** Which `HARDWARE` row you need before it is comfortable. */
  needs: string;
  what: string;
  /**
   * `course` is what every lesson runs. `ci` is a deliberate, registered
   * exception for a lane that cannot run the course model — declared here so it
   * is a decision with a reason attached rather than a second tag that appeared
   * in a compose file one day.
   */
  tier?: "course" | "ci";
  /** For `ci` entries: the only files allowed to name this tag. */
  onlyIn?: string[];
}

/**
 * One tag per role, course-wide.
 *
 * The alternative — each lesson picking its own — is what produced a Phase 2
 * harness judging with `qwen3.6:27b` while Phase 3, its own README and the CI
 * baseline all said `qwen3-coder:30b`. Two judges is two rulers, and a score
 * from one is not comparable to a score from the other, which is the exact
 * mistake Phase 3 spends a lesson warning about.
 */
export const MODELS: CourseModel[] = [
  {
    role: "chat",
    tag: "qwen3.5:9b",
    needs: "16 GB",
    what: "The default chat and tool-calling model for every lesson",
  },
  {
    role: "embed",
    tag: "nomic-embed-text",
    needs: "~8 GB",
    what: "Embeddings for the retrieval phases",
  },
  {
    role: "rerank",
    tag: "BAAI/bge-reranker-base",
    needs: "~8 GB",
    what: "Cross-encoder rerank, ~1 GB of ONNX weights on first run",
  },
  {
    role: "judge",
    tag: "qwen3-coder:30b",
    needs: "32–64 GB",
    what: "The Phase 3 eval judge. On 16 GB, use a hosted judge instead",
  },
  {
    role: "guard",
    tag: "llama-guard3:8b",
    needs: "16 GB",
    what: "The Phase 6 guard model that screens input and output",
  },
  {
    role: "chat",
    tier: "ci",
    tag: "qwen3.5:1.7b",
    needs: "hosted runner (4 vCPU, no GPU)",
    what:
      "The scheduled E2E lane only. A hosted runner cannot finish a 9B CPU " +
      "generation inside the composer's budget, so that lane proves the wiring " +
      "with a small model and says so in its name. Answer quality is not " +
      "measured there — see docker-compose.ci.yml",
    onlyIn: [
      "src/phase8-deploy/01-compose/after/docker-compose.ci.yml",
      "src/verify-e2e.sh",
      ".github/workflows/e2e.yml",
      "app/src/data/reference.ts",
    ],
  },
];

/** The tag every lesson uses. CI-tier entries are exceptions, never defaults. */
export function modelFor(role: ModelRole): CourseModel {
  const found = MODELS.find((m) => m.role === role && (m.tier ?? "course") === "course");
  if (!found) throw new Error(`no canonical model for role ${role}`);
  return found;
}

// ---------------------------------------------------------------------------
// Everything else with a shelf life
// ---------------------------------------------------------------------------

export interface VolatileClaim extends Sourced {
  id: string;
  /** Where in the workbook it is stated, so a reader can go check the prose. */
  where: string;
  /** The claim itself, short enough to compare against the page. */
  claim: string;
}

/**
 * Claims that are true today and will not stay that way.
 *
 * The test of whether something belongs here is not "is it a number" — it is
 * "would a reader be misled by it in a year, and would they have no way to
 * tell". A 512-token chunk size is a design heuristic and ages like one. An
 * ecosystem's server count, a spec revision date and a salary band are
 * observations of a moving world, and stating them without a date is passing
 * off a snapshot as a fact.
 */
export const VOLATILE: VolatileClaim[] = [
  {
    id: "mcp-servers",
    where: "Phase 7 · why MCP won",
    claim: "~10,000 public MCP servers",
    source: {
      label: "MCP servers directory",
      url: "https://github.com/modelcontextprotocol/servers",
    },
    verifiedOn: "2026-07-28",
  },
  {
    id: "mcp-spec",
    where: "Phase 7 · the spec, and what changed",
    claim: "The current MCP spec revision is 2026-07-28, which made transports stateless",
    source: { label: "MCP specification", url: "https://modelcontextprotocol.io/specification" },
    verifiedOn: "2026-07-28",
  },
  {
    id: "tokenizer-drift",
    where: "Phase 1 · counting tokens",
    claim: "tiktoken undercounts Anthropic tokens by 15–20%",
    source: {
      label: "Anthropic token counting API",
      url: "https://docs.anthropic.com/en/docs/build-with-claude/token-counting",
    },
    verifiedOn: "2026-08-01",
  },
  {
    id: "cache-discount",
    where: "Phase 1 · prompt caching",
    claim: "A cache read bills at roughly 10% of the input rate; a write at ~1.25×",
    source: {
      label: "Anthropic prompt caching",
      url: "https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching",
    },
    verifiedOn: "2026-08-01",
  },
  {
    id: "salary-premium",
    where: "Phase 9 · what the market pays",
    claim: "56% wage premium for AI-skilled roles",
    source: {
      label: "PwC Global AI Jobs Barometer",
      url: "https://www.pwc.com/gx/en/issues/artificial-intelligence/job-barometer.html",
    },
    verifiedOn: "2026-07-01",
  },
  {
    id: "salary-bands",
    where: "Phase 9 · what the market pays",
    claim: "US GenAI engineer ~$110–185K; frontier-lab total comp far above it",
    source: {
      label: "Levels.fyi AI/ML engineer",
      url: "https://www.levels.fyi/t/software-engineer/focus/ai-ml",
    },
    verifiedOn: "2026-07-01",
  },
];

export function claim(id: string): VolatileClaim {
  const found = VOLATILE.find((c) => c.id === id);
  if (!found) throw new Error(`no volatile claim registered as ${id}`);
  return found;
}

// ---------------------------------------------------------------------------
// Renderers — the workbook and the READMEs read the same rows
// ---------------------------------------------------------------------------

export function vendorRows(): string[][] {
  return VENDORS.map((v) => [v.vendor, v.flagship, v.daily, v.budget]);
}

export function hardwareRows(): string[][] {
  return HARDWARE.map((tier) => [tier.ram, tier.tags, tier.unlocks]);
}

/** The four-row subset the READMEs carry, as a GitHub-flavoured markdown table. */
export function hardwareSummaryMarkdown(): string {
  const rows = HARDWARE.filter((tier) => tier.summary);
  return [
    "| Tier | What runs | What to know |",
    "|------|-----------|--------------|",
    ...rows.map((tier) => `| ${tier.ram} | ${tier.summary?.runs} | ${tier.summary?.know} |`),
  ].join("\n");
}

/**
 * The `sources` block for a set of claims: every distinct source behind them,
 * and the date of the *stalest* one.
 *
 * The oldest date, not the newest, deliberately. A table is only as fresh as its
 * worst row, and quoting the newest would let one refreshed line make five old
 * ones look current — which is the failure this whole file exists to prevent,
 * dressed up as a citation.
 */
export function sourceNote(claims: Sourced[]): { verifiedOn: string; items: Source[] } {
  const seen = new Map<string, Source>();
  for (const item of claims) seen.set(item.source.url, item.source);
  const [oldest] = claims.map((c) => c.verifiedOn).sort();
  if (!oldest) throw new Error("a sources block with no claims behind it cites nothing");
  return { verifiedOn: oldest, items: [...seen.values()] };
}
