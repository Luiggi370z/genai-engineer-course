// Generated from the shipped course bundle by scripts/extract-data.mjs.
// Edit freely from here on — this file is the source of truth for the content.

import type { PhaseContent } from "../types";

export const foundations: PhaseContent = {
  id: "p1",
  weeks: "Weeks 1–2",
  color: "#0E9F6E",
  title: "Speak Fluent LLM",
  tagline:
    "Get comfortable talking to any model — the big clouds and the one running on your laptop. Everything later debugs back to here.",
  tldr: "One client reaches every provider — hosted and local — with streaming, tools and schema-constrained output behind a single call. You bill each call from the `usage` object rather than an estimate, and build a RAG pipeline by hand so every later stage has a name you already know.",
  objectives: [
    {
      id: "p1-o1",
      text: "**Implement** one client that reaches Anthropic, OpenAI, Google **and local models (Ollama/MLX)** — streaming, tools and structured outputs behind a single call",
    },
    {
      id: "p1-o2",
      text: "**Measure** real cost per call — count with each vendor’s own tokenizer, then bill from the `usage` object rather than an estimate",
    },
    {
      id: "p1-o3",
      text: "**Construct** a small but honest RAG pipeline by hand — chunk, embed, index, retrieve — and justify why each stage exists",
    },
    {
      id: "p1-o4",
      text: "**Constrain** a model’s output with a schema so answers parse on the first try, and compare violation rates hosted vs. local",
    },
    {
      id: "p1-o5",
      text: "**Explain** which part of a prompt is cacheable, and order your messages so the stable prefix survives from one call to the next",
    },
  ],
  concepts: [
    {
      id: "p1-c1",
      title: "Meet the players (June 2026 lineup)",
      tag: "orientation",
      teaches: ["p1-o1"],
      blocks: [
        {
          kind: "p",
          text: "Three storefronts, one skill. Each vendor sells a **flagship** (expensive, brilliant), a **default** (the one you actually use daily), and a **budget tier** (for routing and grunt work). Learn the pattern, not the names — the names change quarterly.",
        },
        {
          kind: "table",
          headers: ["Vendor", "Flagship", "Daily default", "Budget tier"],
          rows: [
            [
              "Anthropic",
              "Opus 4.8 · $5/$25 (Fable 5 above it)",
              "Sonnet 4.6 · $3/$15",
              "Haiku 4.5 · $1/$5",
            ],
            ["OpenAI", "GPT-5.5 · $5/$30", "GPT-5.2 · $1.75/$14", "GPT-5.4 mini/nano"],
            [
              "Google",
              "Gemini 3.1 Pro · $2/$12 (3.5 Pro not GA yet)",
              "Gemini 3.5 Flash · $1.50/$9",
              "3.1 Flash-Lite · $0.25/$1.50",
            ],
          ],
        },
        {
          kind: "p",
          text: "And a fourth player that’s actually you: **open-weight models** — Gemma 4, Qwen 3.5/3.6, gpt-oss, Llama 4 — running on your own machine for **$0 per token**. What fits depends on your RAM; the sizing table in the next card covers everything from an 8GB laptop to a workstation (and the zero-GPU path too).",
        },
        {
          kind: "callout",
          tone: "tip",
          title: "The one lesson that outlives every model",
          text: "Wrap providers behind an **adapter** so swapping models — hosted or local — is a config change, never a refactor. This single design choice powers the cost ladder in Phase 5 and the “runs-anywhere” portfolio flex in Phase 8.",
        },
      ],
    },
    {
      id: "p1-c2",
      title: "Your laptop is a model server now",
      tag: "local-first",
      teaches: ["p1-o1"],
      blocks: [
        {
          kind: "p",
          text: "Think of **Ollama** as Docker for models: `ollama run qwen3.5:9b` and you’re serving. On Apple Silicon, **MLX** squeezes extra speed from unified memory. Here’s the kicker — both expose an **OpenAI-compatible endpoint**, so “local support” costs you one config entry, not a new code path.",
        },
        {
          kind: "table",
          headers: ["Your machine (RAM)", "What runs well (Ollama tags)", "What it unlocks"],
          rows: [
            ["~8 GB", "gemma4:e2b · nomic-embed-text", "Light chat, embeddings, learning the APIs"],
            [
              "16 GB",
              "qwen3.5:9b · gemma4:e4b · gpt-oss:20b",
              "The whole course locally: routing, agents, guard models",
            ],
            [
              "24 GB (or a 24GB GPU)",
              "+ qwen3.6:27b · gemma4:31b (Q4)",
              "Best local coding + generalist quality on consumer hardware",
            ],
            [
              "32–64 GB",
              "+ qwen3-coder 30B-A3B (the MLX-on-Mac favorite)",
              "Agentic coding, bigger contexts, a free local eval judge",
            ],
            [
              "64 GB+ / 80GB GPU",
              "+ qwen3-coder-next · gpt-oss:120b",
              "Open frontier-class reasoning and coding",
            ],
            [
              "No GPU / older laptop",
              "Hosted budget tiers or Ollama cloud models",
              "Same code, same lessons — just a different base_url",
            ],
          ],
        },
        {
          kind: "p",
          text: "Rule of thumb: a model’s Q4 download size ≈ the RAM it needs, plus a few GB of headroom for context. And the RAG essentials — **BGE-M3 embeddings + BGE-reranker-v2** — run on nearly anything, so a fully local retrieval stack is possible at 16 GB.",
        },
        {
          kind: "deepdive",
          title: "That “Q4” in the table — quantization formats, and where the quality cliff is",
          blocks: [
            {
              kind: "p",
              text: "A 27-billion-parameter model at full precision is ~54 GB of weights; the tag you actually pull is ~16 GB. **Quantization** is the difference — storing each weight in 4 bits instead of 16, trading a little accuracy for a model that fits in the RAM you own. It works at all because LLM weights are enormously redundant. Which format you want depends on where it runs.",
            },
            {
              kind: "table",
              headers: ["Format", "Runs on", "Size vs. fp16", "Use it when"],
              rows: [
                [
                  "**Q8_0** (GGUF)",
                  "Ollama, llama.cpp, CPU or GPU",
                  "~50%",
                  "You have RAM to spare and want the quality ceiling — practically indistinguishable from fp16",
                ],
                [
                  "**Q5_K_M** (GGUF)",
                  "same",
                  "~35%",
                  "The step you take when Q4 feels slightly dumb and you have a few GB free",
                ],
                [
                  "**Q4_K_M** (GGUF)",
                  "same",
                  "~28%",
                  "The default, and what Ollama gives you when you don’t specify. Best quality-per-gigabyte on consumer hardware",
                ],
                [
                  "**Q3 / Q2**",
                  "same",
                  "~15–22%",
                  "Almost never. This is where the quality cliff is — instruction-following and arithmetic degrade first, and the model gets subtly worse rather than obviously broken",
                ],
                [
                  "**AWQ / GPTQ**",
                  "GPU serving (vLLM, TGI)",
                  "~28%",
                  "You’re serving many concurrent users from a real GPU. 4-bit like Q4, but laid out for batched GPU inference instead of CPU/unified memory",
                ],
              ],
            },
            {
              kind: "callout",
              tone: "warn",
              title: "The dangerous failure mode is subtle, not loud",
              text: "An over-quantized model doesn’t crash or emit garbage — it starts ignoring one instruction in ten, miscounting, and dropping fields from your schema. It *looks* fine in a demo. This is precisely why Phase 3 makes you build an eval suite: quantization choices are only defensible against numbers you measured yourself.",
            },
          ],
        },
        {
          kind: "p",
          text: "So when should you self-host at all? Four honest reasons — and the bill that comes with them:",
        },
        {
          kind: "list",
          items: [
            "**Privacy** — the data legally cannot leave.",
            "**Volume** — at millions of cheap calls, the GPU amortizes.",
            "**Latency floor** — no network hop.",
            "**The dev loop** — a free, rate-limit-free model to iterate against.",
            "**The bill:** you give up the quality ceiling, million-token windows and tool-calling reliability — and you become the ops team. Most production systems route rather than choose: local for the cheap high-volume steps, hosted for the quality-critical one. Phase 8 turns that into a cost ladder.",
          ],
        },
        {
          kind: "code",
          title: "One client, every provider",
          code: `@dataclass(frozen=True)
class Provider:
    base_url: str | None   # None = vendor default
    api_key: str
    model: str

PROVIDERS = {
    "claude": Provider(None, env("ANTHROPIC_API_KEY"), "claude-sonnet-4-6"),
    "gpt":    Provider(None, env("OPENAI_API_KEY"), "gpt-5.5"),
    "local":  Provider("http://localhost:11434/v1", "ollama", "qwen3.5:9b"),
}

def complete(prompt: str, provider: str = "local", temperature: float = 0.2) -> str:
    p = PROVIDERS[provider]
    client = OpenAI(base_url=p.base_url, api_key=p.api_key)
    resp = client.chat.completions.create(
        model=p.model, temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content

# complete("Classify: 'refund failed twice'")  # runs free, on your machine`,
        },
      ],
    },
    {
      id: "p1-c3",
      title: "Two API tricks you’ll use every single day",
      teaches: ["p1-o1"],
      blocks: [
        {
          kind: "list",
          items: [
            "**Streaming** — tokens arrive as they’re generated (SSE). The difference between an app that feels alive and one that feels frozen. It doesn’t make the answer faster; it makes the *wait* visible, which is why Phase 8 measures time-to-first-token separately from total latency.",
            "**Tool calling** — the model **asks** to run one of your functions; **your code** executes it and reports back. The model never touches your runtime. Local models can do this too (Qwen 3.5+, gpt-oss), just less reliably — validate and retry. Phase 4 turns this single trick into an agent loop.",
          ],
        },
        {
          kind: "callout",
          tone: "tip",
          title: "The third trick got its own card",
          text: "Structured outputs — forcing the model to answer in *your* shape — used to be a bullet here. It earned promotion: it is the difference between an app that parses and one that guesses, and every provider does it differently. Next card.",
        },
      ],
    },
    {
      id: "p1-c-schema",
      title: "Structured outputs: stop parsing, start declaring",
      tag: "schema-first",
      teaches: ["p1-o4"],
      blocks: [
        {
          kind: "p",
          text: "The naive way to get data out of a model is to ask nicely and then parse prose with regex. It works until the day the model says “Sure! Here's the JSON:” and your regex eats the preamble. **Structured outputs** invert the deal: you declare the shape, and the decoder is constrained so no other shape is reachable. Parse failures don’t get *rarer* — for the strict implementations they stop being possible.",
        },
        {
          kind: "p",
          text: "The catch is that “structured output” names four different mechanisms with four different guarantees. Know which one you’re getting, because the weakest of them is just a prompt with good manners.",
        },
        {
          kind: "table",
          headers: ["Provider", "The mechanism", "Guarantee", "Where it bites"],
          rows: [
            [
              "OpenAI",
              '`response_format: {type: "json_schema", strict: true}` (Chat Completions) or `text.format` (Responses)',
              "Grammar-constrained — the schema is enforced during decoding",
              "Strict mode takes a **subset** of JSON Schema: every property must be `required`, `additionalProperties: false` is mandatory, and unions/recursion are limited. A separate `refusal` field can come back instead of your object",
            ],
            [
              "Anthropic",
              'Forced tool use — define the schema as a tool, then `tool_choice: {type: "tool", name: "..."}`',
              "The model must emit that tool’s input, so the shape holds",
              "The answer arrives in a `tool_use` block, not in the text — your parsing code looks different from OpenAI’s even though the intent is identical",
            ],
            [
              "Google",
              '`response_schema` + `response_mime_type: "application/json"`',
              "Constrained decoding against the declared schema",
              "Schema dialect is its own subset; deeply nested optionals are where it complains",
            ],
            [
              "Ollama / local",
              "`format` set to a JSON schema (or `Mode.JSON` via Instructor)",
              "Enforced by the local runtime’s grammar sampler",
              'Small models satisfy the *shape* and still fill it with nonsense. A valid `{"total": 0.0}` is not a correct invoice',
            ],
          ],
        },
        {
          kind: "callout",
          tone: "warn",
          title: "Schema-valid is not fact-correct",
          text: "Constrained decoding guarantees the JSON parses, nothing more. It cannot make a field true. That is exactly the gap Phase 3 exists to measure — validity is a type check, accuracy is an eval.",
        },
        {
          kind: "p",
          text: "Four mechanisms, one interface. **Instructor** wraps all of them behind a Pydantic model: you write the model once, and the provider difference collapses into a `mode=` argument. That is the same adapter bet as card 1 — own the interface, rent the implementation.",
        },
        {
          kind: "code",
          title: "One Pydantic model, hosted or local",
          code: `class Ticket(BaseModel):
    category: Literal["billing", "bug", "account"]   # an enum, not a str
    priority: int = Field(ge=1, le=5)                # constrained, not hoped-for
    summary: str

client = instructor.from_openai(OpenAI())          # hosted: native strict json_schema
# local: same code, one swap — the schema is enforced by Ollama's sampler
# client = instructor.from_openai(
#     OpenAI(base_url="http://localhost:11434/v1", api_key="ollama"),
#     mode=instructor.Mode.JSON,
# )

ticket = client.chat.completions.create(
    model="gpt-5.5",                # or "qwen3.5:9b"
    response_model=Ticket,          # guaranteed shape, zero regex
    max_retries=2,                  # validation errors are fed back, not swallowed
    messages=[{"role": "user",
               "content": "My payment failed three times and I'm furious."}],
)

# The types earn their keep: Literal collapses "Billing"/"billing"/"BILLING" into
# one branch, and ge/le stops a priority of 11 from reaching your router.`,
        },
        {
          kind: "callout",
          tone: "tip",
          title: "Put the constraint in the type, not the prompt",
          text: "“Please answer 1–5” is a request. `Field(ge=1, le=5)` is a contract — checked by Pydantic, and on strict providers by the decoder itself. Every constraint you move from prose into the schema is one fewer thing to validate downstream. Exercise 3 measures how much that buys you, hosted vs. local.",
        },
      ],
    },
    {
      id: "p1-c4",
      title: "Tokens: the taxi meter is always running",
      teaches: ["p1-o2", "p1-o5"],
      blocks: [
        {
          kind: "predict",
          prompt:
            "Two ways to run the same chatbot turn. **(A)** One call with a 40,000-token system prompt, asked once. **(B)** The same 40,000-token prompt, asked 50 times over a conversation, with a short new question each time. Same model, same output length. Before you read on: roughly how much more does B cost than A — 50×, or something else? Commit to a number.",
          answer:
            "If you send it naively, B costs about 50× A, because you are re-sending those 40,000 tokens on every single turn. With **prompt caching** on and the stable prefix ordered first, turns 2–50 bill that prefix at 10–25% of list price, so B lands nearer 10–15× — and it comes back faster too, because cached prefix tokens skip most of the prefill.",
          consolidation:
            "The lesson is not the discount, it is *where the discount lives*: caching keys on an exact prefix match, so a single volatile token near the top — a timestamp, a shuffled list of tools, the user’s name — invalidates everything after it and you silently pay full price. That is why objective 5 is about **message order** rather than about a config flag. Stable content first, volatile content last, and verify with the `cached` field in `usage` rather than trusting that you got it right.",
        },
        {
          kind: "list",
          items: [
            "Models read and write in **tokens** (~4 English characters each; code and non-English text differ a lot). You pay per token in **and** out, and latency grows with every one. Treat the context window like a taxi meter, not a backpack.",
            "**Counting before you send (2026 practice):** every vendor tokenizes differently, so use each vendor’s own counter — Anthropic has a **free `count_tokens` endpoint**, Gemini has a `count_tokens` API, and OpenAI uses the local **tiktoken** library (`o200k_base` for GPT-4o/5.x). Using tiktoken for Claude undercounts by 15–20% — Anthropic says so themselves.",
            "**Measuring after you send:** the `usage` object on every API response is the billing truth — input, output, **cached** tokens (75–90% cheaper when caching hits) and **reasoning** tokens (thinking models bill them as output; effort levels can 2x a bill without touching your prompt). Production teams compute cost from `usage`, never from estimates.",
            "Hosted windows are huge now (1M+). Local models give you 8K–128K — design for the small case and the big one is free.",
            "**More context can make answers worse.** Research (Chroma’s “context rot”) shows accuracy sliding as you stuff the window. A giant window is not a retrieval strategy.",
            "Sampling cheat sheet: `temperature` 0–0.2 for extraction and tools, 0.7+ for brainstorming. Tune temperature **or** top_p — never both.",
          ],
        },
        {
          kind: "code",
          title: "Count before, measure after",
          code: `# BEFORE - preflight count with the VENDOR's counter (tokenizers differ!)
count = anthropic.Anthropic().messages.count_tokens(     # free endpoint
    model="claude-sonnet-4-6",
    messages=[{"role": "user", "content": big_prompt}],
).input_tokens
# OpenAI: tiktoken.get_encoding("o200k_base")  |  Gemini: client.models.count_tokens()

# AFTER - the response's usage object is the billing truth. Meter every call:
PRICE = {"claude-sonnet-4-6": (3.00, 15.00)}             # $/MTok in, out

def cost(model: str, usage) -> float:
    p_in, p_out = PRICE[model]
    cached = getattr(usage, "cache_read_input_tokens", 0)    # ~90% cheaper
    fresh = usage.input_tokens - cached
    return (fresh * p_in + cached * p_in * 0.1
            + usage.output_tokens * p_out) / 1e6             # reasoning bills as output

resp = client.messages.create(model="claude-sonnet-4-6", max_tokens=512,
                              messages=[{"role": "user", "content": q}])
log(cost("claude-sonnet-4-6", resp.usage))   # per-request truth -> your dashboard`,
        },
        {
          kind: "callout",
          tone: "warn",
          title: "Tokenizers change under your feet",
          text: "Anthropic’s Opus 4.7+ and Fable 5 tokenizer produces ~30% more tokens than older Claude models for the same text. Same prompt, new model, bigger bill — one more reason to meter with `usage` instead of trusting cached estimates.",
        },
        {
          kind: "p",
          text: "**Now the discount.** That `cache_read_input_tokens` line in the cost function isn’t a rounding error — cache hits bill at roughly a tenth of the input price. But caching is not something you switch on; it’s something your **prompt layout** either earns or throws away, and the mechanics are unglamorous enough that most people leave the money on the table.",
        },
        {
          kind: "list",
          items: [
            "**It caches a prefix, not a prompt.** The cache key is the exact token sequence from the start of your request up to the cache point. Change one character near the beginning and everything after it is a miss. This is the whole rule; everything below follows from it.",
            "**Therefore: stable content first, volatile content last.** System prompt, tool definitions, few-shot examples, the retrieved document — those go up front. The user’s question, the timestamp, the session id go at the end. Put “Today is 2026-07-31 14:22” in your system prompt and you have built a cache that can never hit.",
          ],
        },
        {
          kind: "deepdive",
          title: "The fine print: minimums, TTL, and who marks the boundary",
          blocks: [
            {
              kind: "list",
              items: [
                "**There is a minimum length.** Anthropic won’t cache a prefix below **1,024 tokens** on Sonnet, or **4,096** on Opus and Haiku. Short prompts simply don’t qualify — which is fine, because they’re cheap anyway.",
                "**The write costs extra, the read is the prize.** On Anthropic a 5-minute cache write runs ~1.25× base input and a read ~0.1×. So the break-even is the *second* hit: caching a prefix you use once is a small loss, caching one you reuse ten times is an ~85% saving on that segment.",
                "**TTL is short and refreshes on use.** The default window is **5 minutes**, extended by each hit; a 1-hour TTL is available at ~2× the write price. Caching suits a burst — an agent loop, a multi-turn conversation, a batch over one big document — not overnight reuse.",
                "**Explicit vs. automatic.** Anthropic makes you mark the boundary with `cache_control` on a content block. OpenAI caches long prefixes automatically and reports `cached_tokens` in `usage`. Both reward the same discipline; only one lets you forget about it.",
              ],
            },
            {
              kind: "code",
              title: "Where you put the marker is the whole design",
              code: `# The cache boundary goes AFTER everything stable. Anything below the marker
# is free to change every call without costing you the hit above it.
resp = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=512,
    system=[
        {"type": "text", "text": TOOL_DOCS + STYLE_GUIDE},        # stable, ~4k tokens
        {"type": "text", "text": retrieved_doc,
         "cache_control": {"type": "ephemeral"}},                 # <-- cache up to here
    ],
    messages=[{"role": "user", "content": question}],             # volatile: below the line
)

u = resp.usage
print(u.cache_creation_input_tokens, u.cache_read_input_tokens)   # write once, then read
# First call: creation > 0, read == 0.  Every call after: read > 0. If read stays 0,
# something above the marker is changing — find it before you blame the vendor.`,
            },
            {
              kind: "callout",
              tone: "tip",
              title: "Mechanics here, strategy in Phase 8",
              text: "This card is only about making the cache *hit*. Deciding **when** caching is the right lever — versus routing the call to a cheaper model, or not making it at all — is the optimization ladder in Phase 8. Order matters there: cache first, because it changes cost without changing behaviour.",
            },
          ],
        },
      ],
    },
    {
      id: "p1-c5",
      title: "Embeddings: GPS coordinates for meaning",
      teaches: ["p1-o3"],
      blocks: [
        {
          kind: "p",
          text: "An embedding turns text into a point in space where **nearby = similar in meaning**. “My card got declined” and “payment failure” land close together even though they share zero words. That’s the magic — and Phase 2 covers exactly where it breaks. Strong hosted options: Gemini Embedding 2, Cohere embed-v4, Voyage. Strong local: **BGE-M3**, Qwen3-Embedding, `nomic-embed-text` — a fully on-laptop RAG stack is normal now.",
        },
        {
          kind: "flow",
          title: "Picking a vector home",
          shape: "decision",
          nodes: [
            {
              label: "Where do the vectors live?",
              sub: "Check the conditions in order and stop at the first yes — they are alternatives, not stages.",
            },
            {
              label: "On Postgres already, <10M vectors?",
              sub: "pgvector — one less system to babysit",
            },
            { label: "Want zero ops?", sub: "Pinecone serverless" },
            { label: "Self-host, fast filters?", sub: "Qdrant" },
            { label: "Billion scale?", sub: "Milvus" },
            { label: "Just prototyping?", sub: "Chroma" },
          ],
        },
        {
          kind: "callout",
          tone: "warn",
          title: "Check the hybrid box early",
          text: "Chroma and plain pgvector don’t do **hybrid search** natively; Qdrant, Weaviate and Milvus do. You’ll want it by Phase 2 — choose accordingly.",
        },
        {
          kind: "code",
          title: "Same meaning → nearby vectors",
          code: `from sentence_transformers import SentenceTransformer
import numpy as np

embed = SentenceTransformer("BAAI/bge-m3")          # runs locally, free
v = embed.encode(["my card got declined",
                  "payment failure",
                  "great weather today"], normalize_embeddings=True)

cos = lambda a, b: float(np.dot(a, b))              # normalized -> dot = cosine
cos(v[0], v[1])   # ~0.7  close in meaning, zero shared words
cos(v[0], v[2])   # ~0.1  unrelated`,
        },
      ],
    },
    {
      id: "p1-c6",
      title: "Your first RAG: a librarian with a highlighter",
      teaches: ["p1-o3"],
      blocks: [
        {
          kind: "p",
          text: "RAG is just this: instead of hoping the model memorized your docs, you **look up the relevant pages and hand them over with the question**. A librarian fetches the right book; a highlighter marks the passage; the model writes the answer from it.",
        },
        {
          kind: "flow",
          title: "Offline: build the library",
          nodes: [
            { label: "Documents" },
            { label: "Chunk" },
            { label: "Embed" },
            { label: "Index" },
          ],
        },
        {
          kind: "flow",
          title: "Online: answer a question",
          nodes: [
            { label: "Question" },
            { label: "Embed it" },
            { label: "Fetch top-k chunks" },
            { label: "Prompt = chunks + question" },
            { label: "Grounded answer" },
          ],
        },
        {
          kind: "list",
          items: [
            "The highest-ROI prompt line in all of GenAI: **“Answer only from the context below. If it’s not there, say you don’t know.”**",
            "Give the model a role, a task, and constraints. Show one example of the output format you want.",
            "For long inputs, sandwich: instructions before **and** after the data.",
            "Small local models need more hand-holding in prompts — annoying at first, but it forces you to write prompts that work everywhere.",
          ],
        },
        {
          kind: "code",
          title: "RAG in one function",
          code: `def rag(question: str, chunks: list[str]) -> str:
    # 1. retrieve the most relevant chunks (real systems embed; this shows the shape)
    top = sorted(chunks, key=lambda c: overlap(question, c), reverse=True)[:3]
    context = "\\n\\n".join(top)
    # 2. ground the model in ONLY those chunks
    prompt = (
        "Answer using ONLY the context. If it's not there, say you don't know.\\n\\n"
        f"Context:\\n{context}\\n\\nQuestion: {question}"
    )
    return complete(prompt, provider="local")       # the Phase-1 client`,
        },
      ],
    },
    {
      id: "p1-c7",
      title: "Zoom out: the whole RAG map",
      tag: "big picture",
      teaches: ["p1-o3"],
      blocks: [
        {
          kind: "p",
          text: "Before we go deep, here’s the **entire production system on one card** — every step, one line each. Don’t memorize it; just get the shape. The rest of the course walks this map station by station, and you can come back here whenever you need to place a new idea.",
        },
        {
          kind: "flow",
          title: "Pipeline A · Ingestion (offline — runs when documents change)",
          nodes: [
            { label: "1 · Load", sub: "PDFs, HTML, wikis, tickets" },
            { label: "2 · Parse & clean", sub: "extract text, strip noise" },
            { label: "3 · Chunk", sub: "split into retrievable pieces" },
            { label: "4 · Enrich", sub: "context sentence + metadata" },
            { label: "5 · Embed", sub: "text → meaning vectors" },
            { label: "6 · Index", sub: "vector store + keyword index" },
          ],
        },
        {
          kind: "flow",
          title: "Pipeline B · Serving (online — runs on every question)",
          nodes: [
            { label: "1 · Guard input", sub: "injection & PII checks" },
            { label: "2 · Embed question" },
            { label: "3 · Retrieve wide", sub: "keywords + vectors, top ~20" },
            { label: "4 · Rerank", sub: "keep the best 3–5" },
            { label: "5 · Assemble prompt", sub: "instructions + chunks + question" },
            { label: "6 · Generate", sub: "grounded answer + citations" },
            { label: "7 · Guard output", sub: "grounded? safe? else abstain" },
            { label: "8 · Trace", sub: "log cost, latency, scores" },
          ],
        },
        {
          kind: "table",
          headers: ["Step", "What it does (one line)", "Where we go deep"],
          rows: [
            [
              "Chunking",
              "Split documents so each piece can answer on its own",
              "Phase 1 exercise + Phase 2",
            ],
            [
              "Embeddings",
              "Turn text into vectors where nearby = similar meaning",
              "Phase 1 exercise + Phase 2",
            ],
            ["Indexing", "Store vectors + keywords for fast lookup", "Phase 1 exercise + Phase 2"],
            ["Hybrid retrieval + rerank", "Cast a wide net, then get picky", "Phase 2"],
            ["Evaluation (RAGAS)", "Score faithfulness & recall; gate changes in CI", "Phase 3"],
            ["Agents & tools", "Let the model act, on a leash", "Phase 4"],
            ["Memory, crew, MCP", "Recall, delegate, and speak the tool protocol", "Phases 5 & 7"],
            ["Guardrails", "Layered defenses on input AND output", "Phase 6"],
            [
              "Cost, caching, observability",
              "Meter every call; cache before you route",
              "Phases 1 & 8",
            ],
          ],
        },
        {
          kind: "callout",
          tone: "tip",
          title: "The one-sentence version",
          text: "Two pipelines: one **builds the library** when documents change, one **answers questions** at request time — with guardrails at both doors and a scoreboard watching everything. If you can draw this map from memory, you already outline like a senior in interviews.",
        },
      ],
    },
  ],
  example: {
    title: "Field story: one codebase, two trust zones",
    text: "A health-tech team needed to summarize clinical notes but couldn’t let patient data leave their machines. They prototyped entirely on Ollama (free, private), proved the workflow, then flipped one config flag to send the **quality-critical** step to a hosted flagship — while PII redaction stayed local forever. Same code, two trust zones, zero refactor. That’s the adapter pattern paying rent.",
  },
  exercises: [
    {
      id: "p1-e1",
      title: "Build the universal client",
      repo: "phase1-foundations/01-universal-client",
      rung: "faded",
      task: "Make complete(prompt, provider) work across Anthropic, OpenAI, Google and Ollama (MLX too if you’re on a Mac). Normalize streaming and tool-call shapes. Start from the template in the companion repo.",
      assesses: ["p1-o1"],
      solution: [
        "One adapter covers every OpenAI-compatible endpoint (OpenAI, Ollama, MLX) — only base_url changes.",
        "Anthropic and Gemini get thin adapters that translate message + tool-call formats.",
        "Model strings live in config. If a model name appears inline in your code, you’ve already lost.",
      ],
    },
    {
      id: "p1-e2",
      title: "Build a cost meter (count before, measure after)",
      repo: "phase1-foundations/02-token-cost-meter",
      rung: "faded",
      task: "Pre-flight: count a big prompt with Anthropic’s free count_tokens endpoint AND with tiktoken, and record how far apart they are. Post-flight: write cost(model, usage) that reads the response’s usage object (including cached tokens) and logs dollars per request. Wire it into your universal client.",
      assesses: ["p1-o2"],
      solution: [
        "The vendor counter vs tiktoken gap on Claude is real (15–20%) — seeing the number cures estimate-trust forever.",
        "usage is the billing truth: input, output, cached, and reasoning tokens. Meter every call; your Phase-6 cost model and Project 2’s cost chart are this function grown up.",
        "Keep the price sheet in config next to the model names — they change together.",
      ],
    },
    {
      id: "p1-e3",
      title: "Extraction shoot-out: cloud vs laptop",
      repo: "phase1-foundations/03-structured-extraction",
      rung: "faded",
      task: "Pull {vendor, date, total} from 20 messy invoices using structured outputs on (a) a frontier model and (b) qwen3.5:9b locally. Compare schema-violation and field-accuracy rates.",
      assesses: ["p1-o4"],
      solution: [
        "Both should hit ~0 schema violations (constrained decoding does that for free).",
        "Field accuracy will differ — and that exact number is your evidence for model tiering in Phase 5. Keep it.",
      ],
    },
    {
      id: "p1-e4",
      title: "Chunk a real document",
      repo: "phase1-foundations/04-chunking",
      rung: "faded",
      task: "Implement two splitters over the provided handbook: fixed-size (~512 tokens, 15% overlap) and heading-aware (split on markdown structure, then size-cap). Print the worst chunk from each — the one that makes least sense alone — and say why.",
      assesses: ["p1-o3"],
      solution: [
        "Fixed-size cuts mid-thought at section boundaries; heading-aware keeps ideas whole but produces uneven sizes. Every chunker trades one failure for another — that’s why Phase 2 measures instead of guessing.",
        "Overlap is the cheap insurance: facts that straddle a boundary survive in one of the two copies.",
      ],
    },
    {
      id: "p1-e5",
      title: "Embed, index, search — a mini vector store",
      repo: "phase1-foundations/05-embed-index",
      rung: "faded",
      task: "Embed your chunks with a local model (nomic-embed-text via Ollama’s OpenAI-compatible endpoint), build an in-memory index with numpy, and write search(query, k) returning the top-k chunks by cosine. Then ask it something phrased with completely different words than the text.",
      assesses: ["p1-o3"],
      solution: [
        "Normalize the vectors once at index time; then cosine similarity is a single matrix–vector product — that IS a vector store, minus the ops.",
        "The different-words query landing on the right chunk is the embeddings “aha.” Also try an exact ID — watch it miss, and remember that miss in Phase 2.",
        "Swapping numpy for Qdrant later changes two functions, not your architecture.",
      ],
    },
    {
      id: "p1-e6",
      title: "Blank editor: rebuild the pipeline from memory",
      rung: "independent",
      task: "Empty directory, `uv init`, one file. From memory — no scrolling back, no `after/` open in another tab — write: a `complete(prompt, provider)` that reaches at least two providers, a `cost(model, usage)` that reads real usage, a chunker, an embedder, and `search(query, k)`. Then answer one question about a document you paste in, and print what the answer cost. Give yourself 90 minutes and keep whatever you produce, however ugly.",
      assesses: ["p1-o1", "p1-o2", "p1-o3"],
      solution: [
        "You reached for the SDK docs, not for exercise 1’s solution. Looking up a parameter name is research; looking up the shape of the thing is a sign the scaffold was doing the thinking.",
        "Your `cost()` reads the response’s `usage` object rather than estimating from character counts. If you multiplied by 4 characters-per-token, you have rebuilt the habit this phase exists to break.",
        "The chunker has an overlap and you can say why. The number matters less than having a reason for it.",
        "It runs end to end. Not elegantly — end to end. A pipeline you can reconstruct from an empty file is a pipeline you actually understand, and this is the first honest signal you have had that the last five exercises stuck.",
        "Where you stalled is the useful output. Note it, then reread that one card. That gap is what the five scaffolds were hiding from you.",
      ],
    },
  ],
  workshop: {
    id: "w-bench",
    title: "Workshop · The model bench",
    subtitle:
      "A CLI that runs one real task across every provider and reports tokens, cost and latency side by side — ranked on the number that actually decides the purchase.",
    repo: "workshops/model-bench",
    assesses: ["p1-o1", "p1-o2", "p1-o4"],
    blocks: [
      {
        kind: "p",
        text: "Your team is about to ship an extraction feature and someone asks the only question that matters: **which model should we use?** The answers in the room are a vendor blog post, a leaderboard nobody can reproduce, and one engineer’s vibe. None of them survive a follow-up question. Build the thing that does.",
      },
      {
        kind: "p",
        text: "This is the one standalone workshop — Workshops 2 through 8 grow a single evolving assistant, and this is the instrument you measure it with. It is also just the three things you already built, pointed at each other: the **adapter** from exercise 1, the **meter** from exercise 2, the **schema** from exercise 3. That is why it belongs here and not in a “tooling” appendix.",
      },
      {
        kind: "flow",
        title: "One task, every candidate, one ranking",
        nodes: [
          { label: "Candidates", sub: "config entries: local · gpt-mini · gpt" },
          { label: "Runner", sub: "injected — fake offline, real in the live tier" },
          { label: "Per case", sub: "time it · meter it · validate it" },
          { label: "Row", sub: "tokens, $, p50/max, success rate" },
          { label: "Rank", sub: "cost per successful parse" },
        ],
      },
      {
        kind: "callout",
        tone: "warn",
        title: "Rank on the right axis or don’t rank at all",
        text: "The most common way a model comparison lies is by sorting on price per token. Tokens are not the unit you buy — **working answers** are. A model at half the price that fails three cases in four is not a bargain, it is a retry loop wearing a discount. `cost_per_success` is the whole reason this bench is worth building.",
      },
      {
        kind: "code",
        title: "The seam you implement",
        code: `# before/src/bench/core.py
def run_case(candidate, prompt, runner, validate, clock) -> Result:
    # TODO: time the call, bill it from usage, validate the reply
    # TODO: this must NEVER raise — a dead vendor is a row, not a crashed run
    ...

@property
def cost_per_success(self) -> float:
    # TODO: spend / answers you can actually use.
    # TODO: decide what zero successes means, and make sorted() agree with you.
    ...`,
      },
      {
        kind: "callout",
        tone: "tip",
        title: "You will keep coming back to this",
        text: "Every later phase that claims a cheap tier is good enough — the tiered crew in Phase 5, the optimization ladder in Phase 8 — needs a number from *your* task mix, not a vendor’s. This is the tool that produces it.",
      },
    ],
    deliverables: [
      {
        id: "w-bench-d1",
        text: "A provider is a **config entry, not a code path** — the runner is injected, and the fast test tier benches four candidates with zero network",
      },
      {
        id: "w-bench-d2",
        text: "Every row reports **tokens, cost and latency**, with cost computed from the response’s `usage` and never from a pre-flight estimate",
      },
      {
        id: "w-bench-d3",
        text: "Each reply is **validated against a schema**, so the row reports a success rate instead of assuming the call worked",
      },
      {
        id: "w-bench-d4",
        text: "Ranking is by **cost per successful parse** — and a test proves the half-price model that fails three in four is the worse buy",
      },
      {
        id: "w-bench-d5",
        text: "A provider that errors or times out becomes a **row with an error**, never a crashed run — one dead vendor can’t hide the other three",
      },
      {
        id: "w-bench-d6",
        text: "`--json` emits the same numbers as the table, so today’s bench can be **diffed against last month’s**",
      },
      {
        id: "w-bench-d7",
        text: "The integration tier runs the identical bench against a **real local model** and reports what it actually costs and how often it holds the schema",
      },
    ],
    stretch: [
      "Add a quality column. The bench measures whether an answer parses, not whether it is right — hand-label expected values and report field accuracy next to cost. You have just built the smallest possible version of Phase 3, which is the honest way to find out why Phase 3 needs four lessons.",
      "Bench prompt caching: send the same long prefix twice and read `cache_read_input_tokens` on the second call. If it stays zero, hunt down what is changing above your cache point.",
      "Add a budget gate — `--max-cost 0.02 --min-success 0.9` exits non-zero when no candidate clears both bars. That is a CI gate, and Phase 8 turns it into one.",
    ],
  },
  checkpoint: [
    {
      id: "p1-q1",
      q: "Why are structured outputs better than parsing prose with regex — and how do they differ from tool calling?",
      a: "Constrained decoding guarantees the output matches your schema, so parse failures basically vanish and the schema lives in code. Tool calling is the model requesting an **action** from your code; structured outputs shape the **final answer**. Actions vs data.",
    },
    {
      id: "p1-q2",
      q: "Your RAG answers feel vague and generic. Name three Phase-1 suspects before blaming the model.",
      a: "(1) Retrieval is fetching irrelevant chunks. (2) The prompt never forces grounding (“answer only from context” missing). (3) The window is overstuffed and the good chunk is lost in the middle. Check those before paying for a bigger model.",
    },
    {
      id: "p1-q3",
      q: "When is a 1M-token window NOT the fix for a retrieval problem?",
      a: "Nearly always at scale: context rot degrades accuracy, cost and latency grow with every token, and your corpus won’t fit anyway. Retrieval picks the right tokens; a big window just tolerates more wrong ones.",
    },
    {
      id: "p1-q4",
      q: "When does a local model beat a hosted one — and what’s the trade?",
      a: "Privacy/data residency, offline work, zero-cost dev loops and bulk batch jobs. You trade away the quality ceiling, big windows, and tool-calling reliability — and you become the ops team.",
    },
    {
      id: "p1-q5",
      q: "Why is the response’s usage object the source of truth for cost, rather than any pre-flight estimate?",
      a: "Estimates drift: tokenizers differ per vendor (tiktoken undercounts Claude 15–20%), tokenizers change between model versions, caching discounts what you actually pay, and reasoning tokens are invisible before the call but billed as output. usage reports what the vendor actually charged — meter it per request and build dashboards on that.",
    },
    {
      id: "p1-q6",
      q: "You added prompt caching to an agent that re-reads the same 6,000-token tool manual every turn, but `cache_read_input_tokens` is always 0. What did you almost certainly do wrong?",
      a: "Something **before** the cache point changes every call. The cache key is the exact token prefix from the start of the request, so a timestamp, a session id, a turn counter or a shuffled tool list sitting in the system prompt invalidates everything after it. Fix: stable content first (tool docs, examples, retrieved document), volatile content last (the user’s turn). Also check the prefix clears the minimum — 1,024 tokens on Sonnet, 4,096 on Opus and Haiku — and that the gap between calls is inside the 5-minute TTL.",
    },
  ],
  resources: [
    {
      label: "Anthropic API docs — models overview",
      url: "https://platform.claude.com/docs/en/about-claude/models/overview",
    },
    {
      label: "Anthropic — token counting endpoint",
      url: "https://platform.claude.com/docs/en/build-with-claude/token-counting",
    },
    {
      label: "OpenAI cookbook — counting tokens with tiktoken",
      url: "https://developers.openai.com/cookbook/examples/how_to_count_tokens_with_tiktoken",
    },
    {
      label: "Anthropic — prompt caching (cache_control, minimums, TTL, pricing)",
      url: "https://platform.claude.com/docs/en/build-with-claude/prompt-caching",
    },
    {
      label: "OpenAI — structured outputs & strict JSON Schema",
      url: "https://developers.openai.com/api/docs/guides/structured-outputs",
    },
    {
      label: "Instructor — one Pydantic model across every provider",
      url: "https://python.useinstructor.com",
    },
    {
      label: "OpenAI API docs — models",
      url: "https://developers.openai.com/api/docs/models",
    },
    { label: "Google Gemini API docs", url: "https://ai.google.dev/gemini-api/docs" },
    { label: "Ollama — model library & OpenAI compatibility", url: "https://ollama.com" },
    { label: "MLX (Apple Silicon inference)", url: "https://github.com/ml-explore/mlx" },
    {
      label: "MTEB leaderboard — embedding rankings",
      url: "https://huggingface.co/spaces/mteb/leaderboard",
    },
    { label: "pgvector", url: "https://github.com/pgvector/pgvector" },
    { label: "Qdrant docs", url: "https://qdrant.tech" },
  ],
};
