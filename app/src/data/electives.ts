/**
 * The electives shelf — optional, and deliberately outside the phase spine.
 *
 * Nothing here has a checkable id, so skipping all of it leaves a student at 100%.
 * That is the design: the nine phases are a claim about what an entry-level GenAI
 * engineer must be able to do, and each of these is a claim about what *some* roles
 * additionally want. Turning them into progress would quietly convert "optional" into
 * "incomplete", which is the exact anxiety a shelf like this is supposed to remove.
 *
 * Each entry states its adoption trigger first, because the failure mode of a shelf
 * like this is a student doing all of it out of FOMO and shipping none of it.
 */
import type { Block, Elective } from "./types";

/** Read before anything else on this page. */
export const electivesGate: { title: string; blocks: Block[] } = {
  title: "Read this before you open any of them",
  blocks: [
    {
      kind: "p",
      text: "Everything on this shelf is **optional**, and skipping all of it costs you nothing — your completion percentage does not know this page exists. The nine phases are the job. These four are specialisms that *some* jobs want, and each one is a real detour: weeks, not evenings.",
    },
    {
      kind: "callout",
      tone: "warn",
      title: "The rule: three job descriptions, or you skip it",
      text: "Open the postings you actually intend to apply to. If a topic appears as a **requirement** in fewer than three of them, close this page and go do another rep of the core loop instead. This is milestone G8 from the dashboard, and it exists because the most common way to stall at this stage is not laziness — it is learning the wrong thing enthusiastically.",
    },
    {
      kind: "p",
      text: "Why the bar is that high: every hour here is an hour not spent on the thing that actually gets you hired, which is **one system you can defend end to end**. A portfolio with a deployed, evaluated, observable assistant beats a portfolio with a fine-tuned model, a GraphRAG demo and no working system — every single time. Depth in the core reads as competence; breadth without depth reads as a tutorial habit.",
    },
    {
      kind: "callout",
      tone: "tip",
      title: "The honest ordering",
      text: "If you are going to do exactly one of these, do the one your target postings mention most, and do it **after** Phase 8 rather than instead of it. If you are between jobs and have the time, fine-tuning has the broadest transfer — mostly because the dataset work teaches you more than the training run does.",
    },
  ],
};

export const electives: Elective[] = [
  {
    id: "el-finetune",
    title: "Fine-tuning & dataset engineering",
    tag: "specialism",
    trigger:
      "Three postings ask for LoRA/QLoRA, PEFT, or “model customization” — or you have a task where prompting plateaued and you have the eval scores to prove it",
    cost: "2–3 weeks to a defensible result. The training run is an afternoon; the dataset is the fortnight.",
    blocks: [
      {
        kind: "p",
        text: "**What it actually is.** You take an open-weight model and nudge its weights toward your task, usually with **LoRA** — training a small pair of low-rank matrices alongside the frozen model instead of updating all its parameters. **QLoRA** does the same on a 4-bit quantized base, which is why this fits on one consumer GPU at all. You are not teaching the model new facts. You are teaching it a **behaviour**: a format, a tone, a decision boundary.",
      },
      {
        kind: "callout",
        tone: "warn",
        title: "Fine-tuning is the wrong answer to most problems that seem to need it",
        text: "It cannot add knowledge — that is retrieval. It cannot fix a task your evals never measured — that is Phase 3. And it cannot repair a prompt you never seriously iterated on. Nearly every “we need to fine-tune” conversation ends, correctly, with a better prompt, a better retriever, or a schema. Reach for weights only after those three are genuinely exhausted, and only if you can say what the current failure rate is.",
      },
      {
        kind: "table",
        headers: ["When it genuinely wins", "Why prompting can’t get there"],
        rows: [
          [
            "A rigid output format at high volume",
            "You can prompt it, but you pay for those instruction tokens on every single call. Baking the format into the weights removes a permanent tax",
          ],
          [
            "A house style or voice",
            "Style is a thousand small choices. Twenty examples in the prompt approximate it; a thousand in training internalises it",
          ],
          [
            "A narrow classification where a small model must match a big one",
            "This is the strongest case: a fine-tuned 8B model beating a frontier model on *your one task*, at a fraction of the cost and latency",
          ],
          [
            "Distilling a frontier model’s behaviour into a cheap one",
            "Generate the training data with the expensive model, then run the cheap one forever. Directly extends the routing argument in Phase 8",
          ],
        ],
      },
      {
        kind: "p",
        text: "**The part that is actually the skill.** Dataset engineering, and it is not glamorous: a few hundred to a few thousand examples that are consistent, deduplicated, decontaminated against your eval set, and correct. Every serious practitioner says the same thing — the model is a commodity, the data is the moat. If Phase 3’s golden set felt like the least exciting phase of this course, notice that it is the same skill, and that this is where it pays.",
      },
      {
        kind: "flow",
        title: "The loop, and where the weeks actually go",
        nodes: [
          { label: "Baseline", sub: "prompt + eval score, written down first" },
          { label: "Dataset", sub: "curate · dedupe · decontaminate ← the fortnight" },
          { label: "Train", sub: "LoRA/QLoRA · one GPU · an afternoon" },
          { label: "Evaluate", sub: "your Phase-3 suite, unchanged" },
          { label: "Decide", sub: "beat the baseline, or throw it away" },
        ],
      },
      {
        kind: "callout",
        tone: "tip",
        title: "The two failure modes, so you can name them",
        text: "**Catastrophic forgetting** — the model gets better at your task and worse at everything else, which you only notice if your eval suite has slices you did *not* fine-tune for. And **overfitting to a small set** — flawless on your 200 examples, useless on the 201st. Both are eval problems before they are training problems, which is why this elective sits after Phase 3 rather than anywhere near the start.",
      },
      {
        kind: "p",
        text: "**The honest cost.** A 4-bit 8B QLoRA run fits on a 16GB consumer GPU or a rented A100 hour; that part is cheap and fast. Then you own a model: versioning it, serving it (see the vLLM elective), re-running it when the base model updates, and explaining in an interview why the extra operational surface was worth it. The interview answer that lands is not “I fine-tuned a model.” It is “prompting got us to 0.71 on this slice, we tried retrieval and got 0.78, a QLoRA run got 0.94, and here is the eval report.”",
      },
    ],
    resources: [
      {
        label: "QLoRA paper — 4-bit finetuning of quantized LLMs",
        url: "https://arxiv.org/abs/2305.14314",
      },
      { label: "LoRA paper — low-rank adaptation", url: "https://arxiv.org/abs/2106.09685" },
      { label: "Hugging Face PEFT docs", url: "https://huggingface.co/docs/peft" },
      { label: "TRL — supervised fine-tuning trainer", url: "https://huggingface.co/docs/trl" },
      {
        label: "Unsloth — fast, low-memory LoRA/QLoRA",
        url: "https://github.com/unslothai/unsloth",
      },
      {
        label: "Axolotl — config-driven fine-tuning",
        url: "https://github.com/axolotl-ai-cloud/axolotl",
      },
    ],
  },
  {
    id: "el-multimodal",
    title: "Voice, vision & browser agents",
    tag: "specialism",
    trigger:
      "Three postings mention voice agents, realtime/speech APIs, document/vision understanding, or browser automation — or the product you want to build is genuinely not text",
    cost: "1–2 weeks per modality. Voice is the deepest: latency budgets and turn-taking are a different engineering problem, not a different API call.",
    blocks: [
      {
        kind: "p",
        text: "**What it actually is.** The same agent you built in Phase 4, with a different input and output pipe. That framing matters, because the temptation is to treat each modality as a new discipline. It isn’t. The loop, the tools, the approval gates and the evals all survive. What changes is the **constraint** each modality imposes, and that constraint is where the engineering lives.",
      },
      {
        kind: "table",
        headers: ["Modality", "What’s genuinely new", "Where teams get it wrong"],
        rows: [
          [
            "**Voice** (realtime speech-to-speech)",
            "A hard end-to-end latency budget — roughly 500–800ms before a conversation stops feeling like one — plus turn-taking, interruption and barge-in handling",
            "Building it as STT → LLM → TTS in series and discovering the pipeline is two seconds deep. Also: no plan for when transcription mishears a name",
          ],
          [
            "**Vision / documents**",
            "Layout *is* information. A table, a form, a signature block and a stamp all mean something a text extraction throws away",
            "Treating a PDF as a wall of text. And skipping the eval: a vision model that reads 95% of invoices correctly fails 1 in 20 payments",
          ],
          [
            "**Browser agents**",
            "A non-deterministic environment with real side effects, where the DOM changes under you and every click is irreversible",
            "No containment. This is Phase 6’s least-privilege lesson with the stakes turned up, and a browser agent with a logged-in session is the single most dangerous thing in this course",
          ],
          [
            "**Image / video generation**",
            "Evaluation is genuinely hard — “is this good?” resists a numeric answer more than anything in Phase 3",
            "Shipping without a human review step, then discovering the brand-safety problem in public",
          ],
        ],
      },
      {
        kind: "callout",
        tone: "warn",
        title: "A browser agent is the highest-risk thing you can build",
        text: "It has a real session, a real cursor, and no undo. Everything Phase 6 taught about least privilege, human-in-the-loop approval on irreversible actions, and spotlighting untrusted content applies **more** here, not less — the page it is reading is attacker-controlled by definition. Run it in a container, on a throwaway account, with approval gates on anything that submits. If that sounds paranoid, read the prompt-injection catalogue again.",
      },
      {
        kind: "p",
        text: "**Why voice is the one worth learning properly.** It is the modality where the engineering is most different from text, because latency stops being a metric and becomes a product constraint. Streaming is not an enhancement, it is table stakes; the P99 discipline from Phase 8 becomes the thing you design around rather than measure afterwards. If you can explain how you kept a voice agent under 800ms round trip and what you cut to get there, you have said something most candidates cannot.",
      },
      {
        kind: "callout",
        tone: "tip",
        title: "The cheap version of this elective",
        text: "Add **one** modality to the assistant you already have rather than building a new project. Voice input on the existing agent loop, or an invoice-image tool alongside the text extractor. You reuse the evals, the guardrails and the traces — and the interview story stays “one system I understand deeply” instead of becoming “four demos”.",
      },
    ],
    resources: [
      {
        label: "OpenAI Realtime API — speech-to-speech",
        url: "https://developers.openai.com/api/docs/guides/realtime",
      },
      {
        label: "LiveKit Agents — realtime voice framework",
        url: "https://docs.livekit.io/agents/",
      },
      {
        label: "Pipecat — open-source voice agent pipelines",
        url: "https://github.com/pipecat-ai/pipecat",
      },
      { label: "Whisper — open speech recognition", url: "https://github.com/openai/whisper" },
      { label: "Playwright — browser automation", url: "https://playwright.dev" },
      {
        label: "Browser Use — LLM-driven browser control",
        url: "https://github.com/browser-use/browser-use",
      },
    ],
  },
  {
    id: "el-graphrag",
    title: "GraphRAG & knowledge graphs",
    tag: "specialism",
    trigger:
      "Three postings mention knowledge graphs, Neo4j, Cypher or GraphRAG — or your retrieval genuinely fails on multi-hop questions and you have the failing eval rows to show it",
    cost: "2–3 weeks, and an ongoing extraction pipeline you now own. The graph is not a one-off build.",
    blocks: [
      {
        kind: "p",
        text: "**What it actually is.** Instead of retrieving chunks by similarity, you first extract **entities and the relationships between them** into a graph, then answer questions by traversing it. A hybrid setup keeps your vector index for “find me passages about X” and uses the graph for “how is X connected to Y”, which are genuinely different questions.",
      },
      {
        kind: "table",
        headers: ["Question", "What plain RAG does", "What a graph does"],
        rows: [
          [
            "“What is our refund window?”",
            "Nails it. One chunk contains the answer",
            "Adds nothing. You built a graph to do a lookup",
          ],
          [
            "“Which suppliers are affected if the Rotterdam warehouse closes?”",
            "Retrieves passages about Rotterdam and passages about suppliers, and hopes the model connects them. Usually it doesn’t",
            "Traverses warehouse → shipments → suppliers. This is the case that justifies the whole elective",
          ],
          [
            "“Summarise the main themes across all 400 incident reports.”",
            "Retrieves the top 20 chunks and summarises those, silently. The answer is confident and unrepresentative",
            "Community detection over the graph gives a genuinely global summary — the strongest documented win for GraphRAG",
          ],
        ],
      },
      {
        kind: "callout",
        tone: "warn",
        title: "The cost is the extraction pipeline, and it never stops",
        text: "Building the graph means an LLM call per chunk to pull out entities and relations — expensive up front, and *permanent*, because every new document needs the same treatment. Then you own entity resolution: “Acme Corp”, “Acme Corporation” and “ACME” are one node or your graph is quietly wrong, and nothing will tell you. Hybrid search plus a reranker (Phase 2) is dramatically cheaper and solves more real problems than most people expect. Exhaust it first.",
      },
      {
        kind: "p",
        text: "**How to know you actually need it.** Not from a blog post — from your own eval suite. Go to the rows your retriever fails and read them. If the failures are “the right chunk wasn’t retrieved”, that is a Phase-2 problem and a graph will not help. If the failures are “the answer requires joining two facts that live in different documents”, you have found the multi-hop case, and that is the honest trigger for this elective. This is the same discipline as everything else in the course: change the architecture in response to a measurement, not a hunch.",
      },
      {
        kind: "callout",
        tone: "tip",
        title: "The cheap experiment first",
        text: "Before standing up Neo4j, try **query decomposition**: have the model split a multi-hop question into single-hop ones, retrieve for each, and compose the answer. It is an afternoon, it uses the retriever you already have, and it solves a surprising share of multi-hop failures. Measure it on the failing rows. If it closes the gap, you have just saved yourself three weeks and a pipeline.",
      },
    ],
    resources: [
      { label: "Microsoft GraphRAG", url: "https://microsoft.github.io/graphrag/" },
      {
        label: "GraphRAG paper — local & global query focus",
        url: "https://arxiv.org/abs/2404.16130",
      },
      {
        label: "Neo4j — GraphRAG for Python",
        url: "https://neo4j.com/docs/neo4j-graphrag-python/current/",
      },
      { label: "LlamaIndex — property graph index", url: "https://docs.llamaindex.ai" },
      { label: "Graphiti — temporal knowledge graphs", url: "https://github.com/getzep/graphiti" },
    ],
  },
  {
    id: "el-serving",
    title: "Serving open models at scale",
    tag: "infrastructure",
    trigger:
      "Three postings mention vLLM, TGI, SGLang, Triton or “LLM inference optimization” — or you have measured sustained concurrency that Ollama cannot hold and a bill that justifies a GPU",
    cost: "1–2 weeks to a working deployment, then ongoing ops. This one is a job, not a project.",
    blocks: [
      {
        kind: "p",
        text: "**What it actually is.** Phase 8 introduced why **vLLM** is fast — PagedAttention, continuous batching, prefix sharing. This elective is the part that phase deliberately skipped: actually running it in production, and the half-dozen decisions that follow the moment you do.",
      },
      {
        kind: "list",
        items: [
          "**Quantization for GPU serving** — AWQ and GPTQ rather than the GGUF quants from Phase 1. Same 4-bit idea, a layout built for batched GPU inference. Measure quality per format on your own evals; the published numbers were not measured on your task.",
          "**Tensor and pipeline parallelism** — splitting one model across several GPUs when it does not fit on one, and understanding why that costs you interconnect bandwidth rather than being free.",
          "**Speculative decoding** — a small draft model proposes tokens and the big one verifies them in a batch. Real speedups, and a correctness argument worth being able to explain: the output distribution is preserved, which is what makes it acceptable at all.",
          "**KV-cache sizing and admission control** — the number that decides your actual concurrency limit. Guess it and you get either wasted GPU or requests dying under load.",
          "**Autoscaling with a cold-start problem** — model weights take minutes to load. Scale-to-zero and low latency are, in practice, mutually exclusive, and pretending otherwise is how you get a 90-second P99.",
        ],
      },
      {
        kind: "callout",
        tone: "warn",
        title: "This is the elective most likely to be a mistake",
        text: "It is genuinely impressive-sounding and almost never the constraint on getting hired. Hosted APIs are cheaper than your time until you are at real volume, and “I served an open model at scale” carries far less weight in an interview than “here is a system with evals, guardrails and traces that I can defend for forty minutes.” Do this one because a specific job asked for it, not because it sounds like the deep end.",
      },
      {
        kind: "p",
        text: "**When it is genuinely right.** Sustained high volume where the GPU amortises against the API bill; a hard privacy or residency constraint that forbids a hosted call at all; a latency floor that a network hop cannot meet; or a fine-tuned model of your own that has to live somewhere (which is how this and the fine-tuning elective end up paired). Notice that all four are *measurements*, not preferences — and that the measuring instrument is the bench you built in Workshop 1.",
      },
      {
        kind: "callout",
        tone: "tip",
        title: "The smallest real version",
        text: "Serve one quantized 8B model with `vllm serve`, point your Phase-1 adapter at it by changing `base_url`, and run the model bench against it at concurrency 1, 8 and 32. You will have a throughput and latency curve you measured yourself, and the interview answer becomes a number instead of a vocabulary list.",
      },
    ],
    resources: [
      { label: "vLLM docs", url: "https://docs.vllm.ai" },
      { label: "PagedAttention / vLLM paper", url: "https://arxiv.org/abs/2309.06180" },
      {
        label: "Hugging Face Text Generation Inference",
        url: "https://huggingface.co/docs/text-generation-inference",
      },
      { label: "SGLang — structured generation & fast serving", url: "https://docs.sglang.ai" },
      {
        label: "AWQ — activation-aware weight quantization",
        url: "https://arxiv.org/abs/2306.00978",
      },
      { label: "Speculative decoding paper", url: "https://arxiv.org/abs/2211.17192" },
    ],
  },
];
