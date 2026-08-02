// Generated from the shipped course bundle by scripts/extract-data.mjs.
// Edit freely from here on — this file is the source of truth for the content.

import type { PhaseContent } from "../types";

export const deploy: PhaseContent = {
  id: "p6",
  weeks: "Weeks 16–17",
  color: "#E11D48",
  title: "Run It in Production",
  tagline:
    "Everything you built has run on your laptop. Now put the assistant and its MCP server on the internet — containerized, CI-gated, observable — and then make it cheaper and faster without making it worse.",
  tldr: "The stack leaves your laptop: containerized, CI-gated on tests, evals and the red-team suite, deployed with health checks and a rollback path, traced with OpenTelemetry. Then the optimization ladder — cache, route, stream — defended on P99 rather than an average.",
  objectives: [
    {
      id: "p6-o1",
      text: "**Containerize** the assistant and its MCP server so the whole stack comes up with one command",
    },
    {
      id: "p6-o2",
      text: "**Build** a CI pipeline that runs tests, evals and the red-team suite — and blocks merges that regress",
    },
    {
      id: "p6-o3",
      text: "**Deploy** to a real host with platform secrets, health checks and a rollback path",
    },
    {
      id: "p6-o4",
      text: "**Instrument** cost, latency and quality with OpenTelemetry so the traces outlive whichever vendor you send them to",
    },
    {
      id: "p6-o5",
      text: "**Optimize** cost and latency in the order that pays — cache, then route, then stream — and defend a P99 budget rather than an average",
    },
  ],
  recall: [
    {
      id: "p6-r1",
      q: "Which parts of an eval suite need no LLM at all? List as many as you can — this decides what your CI can afford to run on every push.",
      a: "Dataset integrity checks, retrieval metrics computed from known document ids, abstention checks, every trajectory metric, aggregation, and the gate logic itself. All deterministic, free, and offline. The judged tier is reserved for what genuinely requires reading meaning, and it runs nightly. That split is the shape of the pipeline you are about to build in objective 2.",
      from: "p-evals-o5",
    },
    {
      id: "p6-r2",
      q: "Cold: name the four context-window moves in priority order, and say which one a summarizer implements.",
      a: "Keep, compress, evict, park. The summarizer is *compress*, and it is the riskiest of the four because it is a lossy write that can launder a guess into an established fact. It comes back here for a production reason: a long-running deployed agent applies these moves thousands of times a day, and a poisoned summary is a bug you can only trace if you kept provenance.",
      from: "p-memory-o2",
    },
    {
      id: "p6-r3",
      q: "You are asked to justify your guardrails to a security reviewer. What is the argument for why filtering is not enough?",
      a: "Filters are probabilistic and attackers iterate, so the design has to survive a bypass rather than assume none. That means containment: least-privilege tools, no unreviewed irreversible actions, an egress allowlist, hard caps in code. In this phase that argument becomes concrete — the red-team suite runs in CI and blocks the merge, which is how a claim about layered defense turns into something a reviewer can verify.",
      from: "p4-o4",
    },
  ],
  concepts: [
    {
      id: "p6-c1",
      title: "Containerize the whole stack",
      tag: "deployment",
      teaches: ["p6-o1"],
      blocks: [
        {
          kind: "p",
          text: "A deployment is only real if a stranger can run it. Your target: `docker compose up` brings the assistant, its MCP server, the vector store, and a local model online together — ideally with **zero API keys** for the demo path. Multi-stage Dockerfiles keep images small; compose wires the services.",
        },
        {
          kind: "code",
          title: "One compose file, the whole system",
          code: `services:
  assistant:
    build: ../workshops/assistant/after   # the capstone image
    ports: ["8000:8000"]                  # the ONLY published port
    environment: [MCP_SERVER=http://mcp:8080/mcp, QDRANT_URL=http://qdrant:6333]
    depends_on:                           # wait for HEALTH, not for start
      mcp:    { condition: service_healthy }
      qdrant: { condition: service_healthy }
      ollama: { condition: service_healthy }
  mcp:                          # same image, run as the MCP server
    build: ../workshops/assistant/after
    command: ["python", "-m", "assistant.mcp_server", "--http"]
  qdrant:
    image: qdrant/qdrant:v1.18.3   # pinned — ':latest' = every reviewer runs a different stack
  ollama:
    image: ollama/ollama:0.32.5    # pulls its models, THEN reports healthy
# (healthchecks elided here — the lesson writes one per service)
# reviewers run ONE command and the assistant + MCP + retrieval all come up.`,
        },
        {
          kind: "callout",
          tone: "tip",
          title: "The zero-key demo is a differentiator",
          text: "Most portfolio repos die in the reviewer’s first minute — missing keys, broken setup. A stack that boots fully on local models from one command proves the system actually runs and respects the reviewer’s ten minutes. Keep a hosted-model path too, behind an env flag, for the quality-critical version.",
        },
      ],
    },
    {
      id: "p6-c2",
      title: "CI that gates on quality, safety, latency and cost",
      tag: "CI/CD",
      teaches: ["p6-o2"],
      blocks: [
        {
          kind: "p",
          text: "Your Phases 3 and 6 gave you suites that now become merge gates: the **RAGAS eval** (quality), the **red-team suite** (safety), plus two budget gates over the same report — **P99 latency** and **cost per golden-set run**. CI runs all four on every pull request; a regression in any one blocks the merge.",
        },
        {
          kind: "p",
          text: 'The report is **version-stamped** (model, prompt, corpus, dataset) — an unstamped report blocks every gate, because numbers without provenance are not evidence. This is what "eval-first" looks like in production: the tests you already wrote, wired to the branch protection.',
        },
        {
          kind: "code",
          title: ".github/workflows/ci.yml — the gates",
          code: `jobs:
  quality:
    steps:
      - run: make test              # unit tests — the fast, offline tier
      - run: make eval              # quality gate: faithfulness/recall bars
  safety:
    steps:
      - run: make redteam           # fails if any gated tool fires unapproved
  budgets:
    steps:
      - run: make latency           # P99 gate — the tail, not the average
      - run: make cost              # spend gate — fail here, not on the invoice
      - run: make prove-gates       # seeded regressions must BLOCK
# separate REQUIRED jobs, not one averaged score: a safety bypass, a quality
# regression, and a budget blowout are different incidents. No green, no ship.`,
        },
        {
          kind: "list",
          items: [
            "**Full evals nightly, a smoke subset per PR** — LLM-as-judge eval costs real money and time, so don’t run all 50 questions on every commit.",
            "**Pin the judge in CI** (model + prompt + temperature 0) so scores are comparable across runs, exactly as in Phase 3.",
            "**Cache judge calls** keyed on input so unchanged questions don’t re-bill.",
          ],
        },
      ],
    },
    {
      id: "p6-c3",
      title: "Deploy, watch, and roll back",
      tag: "production",
      teaches: ["p6-o3", "p6-o4"],
      blocks: [
        {
          kind: "list",
          items: [
            "**Pick a cheap host:** Fly.io, Render, Railway, or a small VM. Container in, URL out. Your MCP server deploys the same way — and now needs its Phase-7 auth (Bearer or OAuth), because it’s on the internet.",
            "**Secrets via the platform’s secret manager**, never in the image or the repo. The compose env-var discipline pays off here.",
            "**Health checks + rollback:** a `/health` endpoint the platform pings, and keep the previous image so a bad deploy reverts in one click.",
            "**Observability is not optional in production:** trace every request for cost, latency, and a sampled faithfulness score. You can’t fix what you can’t see — and you can’t compare two weeks you never recorded.",
            "**Watch the bill:** the Phase-1 usage meter feeding a dashboard is how you catch a cost runaway before it catches you.",
          ],
        },
        {
          kind: "p",
          text: "One decision inside that third bullet is worth more than the rest of this card: **instrument against OpenTelemetry, not against a vendor SDK.** If your spans are OTel spans, the vendor is an environment variable. If they are `langfuse.trace(...)` calls scattered through the agent loop, the vendor is a refactor — and you will not do it.",
        },
        {
          kind: "deepdive",
          title: "The portable observability stack, layer by layer",
          blocks: [
            {
              kind: "table",
              headers: ["Layer", "What it is", "Why it’s the portable choice"],
              rows: [
                [
                  "**OpenTelemetry**",
                  "The CNCF standard for traces, metrics and logs. `opentelemetry-sdk` plus an exporter",
                  "Vendor-neutral by design and already in your non-AI services. One tracing story for the whole system, not a special one for the LLM parts",
                ],
                [
                  "**OpenInference / GenAI conventions**",
                  "Agreed *attribute names* for LLM spans: `llm.model_name`, `llm.token_count.prompt`, tool and retrieval spans",
                  "Conventions are what make a trace legible to a tool that has never seen your code. Invent your own attribute names and every dashboard is bespoke",
                ],
                [
                  "**The backend**",
                  "Langfuse v4, Phoenix, Braintrust, or your existing APM",
                  "Interchangeable *because* of the two rows above. Langfuse v4 is OTel-native; Phoenix reads OpenInference directly",
                ],
                [
                  "**The exporter**",
                  "OTLP over HTTP to a collector — or `InMemorySpanExporter` in tests",
                  "The same instrumentation runs in CI with no network and no vendor account, which is how the tracing code gets tested at all",
                ],
              ],
            },
            {
              kind: "code",
              title: "Instrument once, choose the vendor later",
              code: `tracer = trace.get_tracer("assistant")

def answer(question: str) -> str:
    with tracer.start_as_current_span("llm.call") as span:
        span.set_attribute("llm.model_name", model)          # convention, not invention
        resp = client.chat.completions.create(...)
        u = resp.usage
        span.set_attribute("llm.token_count.prompt", u.prompt_tokens)
        span.set_attribute("llm.token_count.completion", u.completion_tokens)
        span.set_attribute("cost.usd", cost(model, u))       # the Phase-1 meter, on a span
        return resp.choices[0].message.content

# Where it ships is configuration, not code:
#   OTEL_EXPORTER_OTLP_ENDPOINT=https://cloud.langfuse.com/api/public/otel
#   OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:6006/v1/traces   # local Phoenix
# and in tests: InMemorySpanExporter, so the assertions need no network at all.`,
            },
            {
              kind: "callout",
              tone: "tip",
              title: "A span you can assert on is a span you’ll keep",
              text: "Tracing rots faster than anything else in a codebase, because nothing fails when it silently stops recording. An in-memory exporter fixes that: your test asserts the span exists and carries a cost attribute, so deleting the instrumentation breaks the build. Exercise 3 does exactly this.",
            },
          ],
        },
        {
          kind: "flow",
          title: "The path to production",
          nodes: [
            { label: "docker compose up", sub: "works locally" },
            { label: "CI green", sub: "tests + eval + red-team" },
            { label: "Deploy", sub: "host + secrets + health" },
            { label: "Observe", sub: "cost / latency / quality" },
            { label: "Roll back if needed", sub: "previous image ready" },
          ],
        },
        {
          kind: "callout",
          tone: "warn",
          title: "The MCP server changed trust zones",
          text: "On your laptop the MCP server was stdio — no auth needed. The moment you deploy it as an HTTP service, it’s reachable by anyone who finds the URL. Turn on the Phase-7 auth (Bearer for internal, OAuth 2.1 for public) and validate token audience. A deployed server without auth is an open door to your tools.",
        },
      ],
    },
    {
      id: "p6-c-ladder",
      title: "The optimization ladder: cache, route, stream",
      tag: "cost & latency",
      teaches: ["p6-o5"],
      blocks: [
        {
          kind: "predict",
          prompt:
            "Your deployed assistant averages **1.9s** per response, but P99 is **8.4s** and users are complaining about “sometimes it just hangs.” You swap in a model that is genuinely 40% faster. Predict what each number does. Then decide: is that the change you would have made first?",
          answer:
            "The average drops nicely, to roughly 1.3s, and your dashboard looks great. P99 barely moves — it might land around 7.5s. The tail is not made of slow generations; it is made of cache misses, cold starts, a retry after a 429, a reranker pass over too many candidates, one tool call waiting on a slow upstream. A faster model shrinks one term in a sum that the other terms dominate.",
          consolidation:
            "The general form is worth keeping: **averages describe the common path, and complaints come from the tail.** Users do not experience your mean. This is why the objective says defend a P99 budget, and why the ladder below starts with caching rather than with a model swap — caching removes whole requests from the tail instead of shaving each one, and it is the cheapest, most reversible rung. Take the rungs out of order and you get a system that is faster on the dashboard and still hangs.",
        },
        {
          kind: "p",
          text: "Your system works and it is online. It is also slower and more expensive than it needs to be, and you have a finite number of changes you can make before you break it. So the question is not *what* can be optimized — it is **what order**. The ladder below is sorted by risk, cheapest and safest first, and taking the rungs out of order is how teams end up with a fast system that gives worse answers.",
        },
        {
          kind: "table",
          headers: ["Rung", "The lever", "Typical effect", "What it costs you"],
          rows: [
            [
              "1",
              "**Prompt caching** — stabilize the prefix so repeated context bills at cache rates (`p1-c4`)",
              "Cuts input cost on repeated prefixes; also cuts latency, since cached tokens aren’t re-processed",
              "Nothing. Same model, same prompt, same answer — this is the only rung with no behavioural risk at all",
            ],
            [
              "2",
              "**Exact-match caching** — same question, same context, return the stored answer",
              "Removes the call entirely for the duplicate share of your traffic",
              "Staleness. Needs a key that includes the context and a TTL you chose deliberately",
            ],
            [
              "3",
              "**Semantic caching** — a *similar* question reuses a stored answer above a similarity threshold",
              "Extends the hit rate past exact duplicates",
              "Real risk: the wrong answer to a nearly-right question. The threshold is a quality decision and belongs in your eval suite",
            ],
            [
              "4",
              "**Routing** — send easy work to a cheap or local model, keep the frontier model for the hard cases",
              "The biggest lever on a mixed workload, because most requests are not hard",
              "Quality, unless you measure it. Requires a classifier you trust and a per-tier eval score",
            ],
            [
              "5",
              "**Streaming** — send tokens as they’re generated",
              "Time-to-first-token drops to near nothing; *perceived* latency transforms",
              "Nothing in cost, and nothing in quality — but it changes zero about total latency, so don’t report it as a speedup",
            ],
            [
              "6",
              "**Batching / async** — group the work that nobody is waiting for",
              "Throughput on ingestion, summarization, backfills",
              "Only applies off the request path. Batching something a user is waiting for makes it worse",
            ],
          ],
        },
        {
          kind: "callout",
          tone: "warn",
          title: "Rungs 3 and 4 are quality changes wearing a cost-saving costume",
          text: "Caching a prefix cannot change an answer. A semantic cache and a router absolutely can. This is exactly why Phase 3 came before this one: run the eval suite after each rung and report cost **and** score together. A 60% cheaper system that scores four points lower is not an optimization, it is an undeclared quality cut — and in an interview, someone will find it.",
        },
        {
          kind: "flow",
          title: "Where each rung sits on the request path",
          nodes: [
            { label: "Request", sub: "user question + context" },
            { label: "Cache lookup", sub: "exact, then semantic (threshold)" },
            { label: "Route", sub: "classify → local · cheap · frontier" },
            { label: "Call", sub: "stable prefix first → prompt cache hits" },
            { label: "Stream", sub: "first token out immediately" },
            { label: "Trace", sub: "cost, tokens, tier, cache hit, ms" },
          ],
        },
        {
          kind: "deepdive",
          title: "Then measure it properly: the tail is the budget, not the mean",
          blocks: [
            {
              kind: "p",
              text: "**The average latency of an LLM app is a number that describes nobody.** Response times are heavily right-skewed: a long retrieval, a cache miss, a reasoning burst, a retry after a schema violation. The mean hides all of it behind the fast majority. Your users experience the tail, so the tail is the budget — set a **P99** (or at least P95), alert on it, and treat the mean as a curiosity.",
            },
            {
              kind: "code",
              title: "The number that goes in the SLO",
              code: `# Mean vs tail on the same 100 requests: same system, two very different stories.
mean = sum(latencies) / len(latencies)          # 480 ms  — "feels fast"
p50  = percentile(latencies, 50)                # 300 ms
p95  = percentile(latencies, 95)                # 2,100 ms
p99  = percentile(latencies, 99)                # 8,400 ms — one user in a hundred waits 8s

# A budget is a bar you can fail, plus a rule for what happens when you do.
def safe_to_promote(new_p99_ms: float, prev_p99_ms: float, budget_ms: float) -> bool:
    if new_p99_ms > budget_ms:
        return False                            # over budget: never ship it
    return new_p99_ms <= prev_p99_ms * 1.2      # or a 20% tail regression: block it

# Report the pair, always. "p50 300ms / p99 8.4s" is a system with a problem.
# "480ms average" is the same system with the problem edited out.`,
            },
            {
              kind: "callout",
              tone: "tip",
              title: "You already have the measuring instrument",
              text: "Every rung here needs the same evidence: cost and latency per request, sliced by tier and by cache outcome. That is the trace from the previous card and the bench from Phase 1. Build the measurement first — otherwise you are not optimizing, you are guessing with extra steps.",
            },
          ],
        },
      ],
    },
    {
      id: "p6-c-serving",
      title: "Serving at scale: vLLM, PagedAttention, continuous batching",
      tag: "when you outgrow Ollama",
      teaches: ["p6-o5"],
      blocks: [
        {
          kind: "p",
          text: "Ollama has carried this entire course, and for one user at a time it is excellent. It is also the wrong tool the moment you have **concurrent** users, because it is optimized for your laptop rather than for throughput. When that day comes, the answer in 2026 is **vLLM** — and it is worth understanding *why* it is faster, because that reasoning is a common interview question and the answer is genuinely elegant.",
        },
        {
          kind: "list",
          items: [
            "**PagedAttention** — the KV cache is stored in fixed-size blocks with a lookup table, exactly the way an operating system pages memory. Naive serving pre-allocates a contiguous block for each request's *maximum* possible length, so most of that GPU memory sits reserved and unused. Paging removes the fragmentation, which means far more requests fit on the same card.",
            "**Continuous batching** — instead of waiting for every request in a batch to finish, a finished sequence is evicted and a queued one takes its slot on the next step. With mixed response lengths that keeps the GPU busy rather than idling behind the single slowest generation in the batch.",
            "**Prefix sharing** — requests that begin with the same system prompt or document share those KV blocks instead of each holding a copy. The same prefix discipline that earns you a prompt-cache hit with a hosted vendor earns you memory back here.",
            "**An OpenAI-compatible server** — `vllm serve <model>` speaks the same API your adapter has been calling since Phase 1. Which means, if you built the adapter properly, moving from Ollama to vLLM is a `base_url` change and nothing else.",
          ],
        },
        {
          kind: "callout",
          tone: "warn",
          title: "You almost certainly don’t need this yet",
          text: "vLLM needs a real GPU, and the operational surface — weights, drivers, memory tuning, an autoscaling story — is a job, not an afternoon. Self-hosted serving pays off at sustained high volume, or under a hard privacy constraint. Below that, a hosted budget tier is cheaper than your own time. Reach for this when you can point at the volume, not because it sounds impressive.",
        },
        {
          kind: "table",
          headers: ["Serving choice", "Good for", "Reach for it when"],
          rows: [
            [
              "**Hosted API**",
              "Almost everything, especially before you have traffic",
              "Default. Stop here unless you can name the constraint that breaks it",
            ],
            [
              "**Ollama**",
              "Development, single-user tools, privacy-bound desktop work",
              "You want zero cost per token and one request at a time — this whole course",
            ],
            [
              "**vLLM (or TGI / SGLang)**",
              "Many concurrent users on open weights, on your own GPU",
              "You have measured sustained concurrency and a bill that justifies a GPU",
            ],
          ],
        },
        {
          kind: "p",
          text: "The serving-at-scale rabbit hole — quantized GPU formats (AWQ, GPTQ), tensor parallelism, speculative decoding, autoscaling — sits on the **Electives shelf** rather than in this phase. It is a real specialism and a genuine detour: nothing else in the course depends on it, and no portfolio reviewer will ask for it unless the job description does.",
        },
      ],
    },
  ],
  example: {
    title: "Field story: the demo that deployed itself",
    text: "An engineer put their hardened assistant + MCP server behind one `docker compose up` and a Fly.io deploy, with CI running evals and the red-team suite on every PR. In the interview, instead of describing the system, they shared the repo, the reviewer ran one command, and it came up — assistant, MCP, retrieval, all of it, no keys. The offer conversation started ninety seconds later. Working software beats slides every time.",
  },
  exercises: [
    {
      id: "p6-e1",
      title: "Containerize the assistant + MCP",
      repo: "phase8-deploy/01-compose",
      rung: "faded",
      task: "Write structural checks over the compose file (parsed YAML: pinned images, a healthcheck per service, health-gated depends_on, one published port), watch them fail on the shipped first draft, then fix the wiring until the whole stack — capstone assistant, MCP server, Qdrant, Ollama — is one trustworthy `docker compose up`, zero API keys.",
      assesses: ["p6-o1"],
      needs: ["p3-o2", "p5-o3"],
      solution: [
        "condition: service_healthy for ordering — a started Qdrant is not a ready Qdrant; env vars for every URL; the ollama service pulls its models before reporting healthy.",
        "Test the reviewer experience: fresh clone, one command, does it come up? `verify-e2e.sh` automates exactly that.",
      ],
    },
    {
      id: "p6-e2",
      title: "The CI gate",
      repo: "phase8-deploy/02-ci",
      rung: "faded",
      task: "Build the four independently failing merge gates — quality (faithfulness/recall), safety (zero red-team bypasses), P99 latency and cost — over a version-stamped report, wire them into the make targets a GitHub Actions workflow calls, and prove each gate can actually block with the seeded regressions (`make prove-gates`).",
      assesses: ["p6-o2"],
      needs: ["p-evals-o5", "p4-o4"],
      solution: [
        "Smoke subset per PR, full evals nightly; pin and cache the judge.",
        "Branch protection is the point — an eval regression or a red-team bypass must actually block the merge, not just warn.",
      ],
    },
    {
      id: "p6-e3",
      title: "Deploy it and watch it (with OpenTelemetry)",
      repo: "phase8-deploy/03-deploy-observe",
      rung: "faded",
      task: "Deploy the stack to a cheap host with platform secrets, a health check, and the MCP server’s Phase-7 auth turned on. Then instrument it with real OpenTelemetry spans carrying OpenInference attributes — model, token counts, cost, tier — and compute P95, daily spend and the rollback guard from the exported spans rather than from a side-channel of your own.",
      assesses: ["p6-o3", "p6-o4"],
      needs: ["p1-o2", "p5-o4"],
      solution: [
        "Secrets from the platform manager, never the image. /health for the platform to ping. Keep the previous image for rollback.",
        "The deployed MCP server now needs auth — Bearer for internal, OAuth 2.1 if public. Confirm token audience validation.",
        "An InMemorySpanExporter makes the whole tracing layer unit-testable with no collector and no vendor account — which is the only reason tracing code ever stays correct. The exporter is the one line that differs between CI and production.",
        "Read your metrics off the spans. The moment latency lives in one place and spans in another, they disagree, and you will trust the wrong one.",
      ],
    },
    {
      id: "p6-e4",
      title: "Climb the ladder: cache, route, and defend a P99",
      repo: "phase8-deploy/04-cost-latency",
      rung: "faded",
      task: "Take the request path and add the first four rungs in order: an exact cache, a semantic cache with a similarity threshold, and a tier router with a cost ceiling. Then measure — P50, P95, P99 and cost per request, before and after each rung. Report the pair (cost and quality) every time, and make the budget gate fail a run that blows the tail.",
      assesses: ["p6-o5"],
      needs: ["p1-o2", "p-evals-o5", "p-memory-o3"],
      solution: [
        "The cache key has to include everything that changes the answer — question plus retrieved context plus model plus tier. A key that ignores the context serves yesterday's document to today's question.",
        "The semantic threshold is a quality decision, not a tuning constant. Sweep it, look at what gets wrongly reused at each value, and pick with the evidence in front of you — the same method as the judge threshold in Phase 3.",
        "Router savings are only real if the cheap tier holds its eval score. Report cost and score together or don't report the saving.",
        "P99 out of 100 requests is one request. Do not build an SLO on a single sample — either collect more, or state your confidence honestly.",
      ],
    },
    {
      id: "p6-e5",
      title: "Blank editor: containerize and instrument something you did not build",
      rung: "independent",
      task: "Empty directory. Take a small service you did not write — a sample FastAPI app, an open-source tool, a friend’s side project — and from nothing produce a multi-stage Dockerfile, a compose file bringing it up alongside one dependency, a real health check, and OpenTelemetry spans on its main request path carrying model, token and cost attributes if it calls a model, or duration and outcome if it does not. Then prove the tracing with an in-memory exporter and no collector running. Done means a stranger can `docker compose up` and see spans.",
      assesses: ["p6-o1", "p6-o4"],
      needs: ["p1-o2"],
      solution: [
        "You wrote the Dockerfile without a template. Everyone can copy a multi-stage build; being able to produce one means you know which stage installs the toolchain and why the final image should not contain it.",
        "The health check reports something real — a dependency reachable, not just the process alive. A `/health` that returns 200 whenever Python is running tells the platform nothing and will happily keep a broken container in rotation.",
        "No secrets in the image or the compose file, and you can say where they should come from instead. This is the mistake that survives into real jobs, so catching it on someone else’s service is cheap practice.",
        "Your span assertions run with an in-memory exporter and no vendor account. Tracing code that can only be verified by looking at a dashboard is tracing code that quietly rots, and this is the single habit from this phase most worth keeping.",
        "The attributes are on the spans, not in a parallel log line. The moment your latency numbers live somewhere other than your traces, the two disagree and you will trust the wrong one.",
        "It came up on the first try for someone else. Not for you, on your machine, with your Python version — that is the whole meaning of “containerized”, and the unfamiliar service is what stops your own setup from doing the work invisibly.",
      ],
    },
  ],
  workshop: {
    id: "w-deploy",
    title: "Workshop · The deployed stack",
    subtitle:
      "See the assistant before you optimize it: OpenTelemetry spans around the loop and every tool, then an answer cache that knows what it must refuse to store.",
    repo: "workshops/assistant",
    assesses: ["p6-o1", "p6-o2", "p6-o3", "p6-o4", "p6-o5"],
    needs: ["p1-o2", "p-evals-o5", "p4-o4"],
    blocks: [
      {
        kind: "p",
        text: "The assistant works, it is hardened, and it speaks MCP. It is also a black box that costs an amount nobody has measured and takes a length of time nobody has bounded. This workshop closes that gap in the only order that is safe: **see it, then make it cheaper without making it worse.**",
      },
      {
        kind: "flow",
        title: "Two modules, and why the second needs the first",
        nodes: [
          { label: "traced_registry", sub: "every tool wrapped at the seam" },
          { label: "agent.run span", sub: "steps · paused for approval" },
          { label: "Read the tree", sub: "time_by_tool · gated_tool_calls" },
          { label: "AnswerCache", sub: "offer(), not put()" },
          { label: "Refusals", sub: "side effects · paused · step cap" },
        ],
      },
      {
        kind: "p",
        text: "**Why the tools are wrapped rather than edited.** Tracing is a cross-cutting concern, and cross-cutting concerns rot when they live inside every implementation: somebody adds a tool, forgets the decorator, and six weeks later there is a hole in the trace nobody can explain. Wrapping the registry makes instrumentation a property of the *seam*, so a new tool is traced whether its author thought about it or not.",
      },
      {
        kind: "callout",
        tone: "warn",
        title: "Caching an agent is not caching RAG",
        text: "A RAG answer is a pure function of a question and a corpus. An agent run sends messages and books meetings. Cache “text my boss the summary” and the second request returns instantly — and no message is sent. Nothing errors, nobody is paged, and the user finds out from their boss. That is why the API is `offer()` rather than `put()`: the caller proposes and the policy decides, reading the **trace** to see which gated tools actually fired.",
      },
      {
        kind: "code",
        title: "The seam you implement",
        code: `# before/src/assistant/observe.py
def traced_registry(registry: dict[str, Tool], tracer) -> dict[str, Tool]:
    # TODO: wrap every tool's body in a span — mark ERROR, then RE-RAISE
    # TODO: an observability layer that swallows an exception has turned a
    #       visible failure into a silent wrong answer
    ...

def gated_tool_calls(spans) -> list[str]:
    # TODO: which irreversible tools actually fired. A safety report, and the
    #       input the cache reads before it stores anything.
    ...

# before/src/assistant/cache.py
def is_cacheable(result, gated_tools_fired) -> bool:
    # TODO: refuse a paused run, a side-effecting run, a step-cap run, an empty
    #       answer. Be conservative: a miss costs money you can graph, a wrong
    #       hit costs trust you cannot.
    ...`,
      },
      {
        kind: "callout",
        tone: "tip",
        title: "The observability layer is not just a dashboard feed",
        text: "It is the input to a safety decision. `cached_run` asks the trace which gated tools fired before it will store an answer — because you cannot safely cache what you cannot see. That coupling is the reason this workshop does tracing first and caching second.",
      },
    ],
    deliverables: [
      {
        id: "w-deploy-d1",
        text: "The whole stack comes up with **one command and zero API keys** — assistant, MCP server, retrieval and a local model",
      },
      {
        id: "w-deploy-d2",
        text: "CI runs tests, a smoke eval and the red-team suite as **required checks**, so a quality or safety regression blocks the merge",
      },
      {
        id: "w-deploy-d3",
        text: "Deployed to a real host with **platform secrets, a health check and a rollback path**, and the MCP server’s auth turned on",
      },
      {
        id: "w-deploy-d4",
        text: "Every tool is traced by **wrapping the registry** — a test proves a newly-added tool is instrumented without its author doing anything",
      },
      {
        id: "w-deploy-d5",
        text: "A failing tool is marked **ERROR on its span and still raises**; the root `agent.run` span carries step count and whether it paused",
      },
      {
        id: "w-deploy-d6",
        text: "`gated_tool_calls` reports **which irreversible tools actually fired**, and a contained run reports none",
      },
      {
        id: "w-deploy-d7",
        text: "The cache **refuses** a paused run, a side-effecting run, a step-cap run and an empty answer — one test per rule",
      },
      {
        id: "w-deploy-d8",
        text: "A repeated read-only question doesn’t rerun the agent; a side-effecting one **reruns every time** — both asserted",
      },
      {
        id: "w-deploy-d9",
        text: "P99 and cost per request are reported **next to the eval score**, before and after the caching rung",
      },
    ],
    stretch: [
      "Ship the spans somewhere real: point `OTEL_EXPORTER_OTLP_ENDPOINT` at a local Phoenix or a Langfuse project and look at the actual tree. Change nothing in observe.py — if you have to, your instrumentation isn’t portable yet.",
      "Put cost on the spans with the Phase-1 meter, then find the single most expensive request you have ever made and explain, from the trace alone, why it cost that.",
      "Add the semantic layer from exercise 4 and sweep the threshold on your own traffic. Report the wrong-reuse count, not just the hit rate.",
      "Gate the deploy on the tail: fail CI when P99 across your golden set busts the budget, using the rollback guard from exercise 3.",
    ],
  },
  checkpoint: [
    {
      id: "p6-q1",
      q: "Why is the zero-API-key `docker compose up` worth the effort?",
      a: "It proves the system actually runs (most repos don’t), demonstrates local-model fluency, and respects a reviewer’s limited time. Friction kills portfolio reviews and demos; removing it is a real edge.",
    },
    {
      id: "p6-q2",
      q: "What changes about your MCP server the moment you deploy it remotely?",
      a: "It leaves the safe stdio/OS-isolation trust zone and becomes reachable by anyone with the URL. It now needs Phase-7 auth — Bearer for internal, OAuth 2.1 + PKCE for public — with token-audience validation. A deployed server without auth is an open door.",
    },
    {
      id: "p6-q3",
      q: "What belongs in the CI gate for a GenAI app, beyond normal tests?",
      a: "The eval suite (RAGAS quality gate), the red-team suite (safety gate), and the two budget gates — P99 latency and cost per eval run — all as required checks over a version-stamped report. A merge that regresses faithfulness, lets a landed injection fire a gated tool, or blows the tail-latency or spend budget should be blocked, not merged with a warning.",
    },
    {
      id: "p6-q4",
      q: "Your bill is too high. Why start with caching rather than with routing, when routing saves more?",
      a: "Because caching cannot change an answer and routing can. Rungs are ordered by risk, not by size: prompt caching and exact-match caching are behaviour-preserving, so they are free wins you can ship without re-running the eval suite. A semantic cache and a router are quality changes — they need a threshold or a classifier you have measured, and they need cost reported alongside the eval score. Take the safe savings first; you may not need the risky ones.",
    },
    {
      id: "p6-q5",
      q: "You report “average latency 480ms” and the interviewer pushes back. Why?",
      a: "Because LLM latency is heavily right-skewed and the mean describes nobody. Retrieval misses, cache misses, reasoning bursts and schema retries all live in the tail, and the fast majority hides them. That system might be p50 300ms and p99 8.4s — one user in a hundred waiting eight seconds. Quote the pair, budget on P99 (or at least P95), and alert on the tail. Also say your sample size: a P99 from 100 requests is a single data point.",
    },
    {
      id: "p6-q6",
      q: "Why instrument with OpenTelemetry rather than your observability vendor’s SDK?",
      a: "Portability, and it is cheap to get right up front. Every LLM observability product speaks OTel or exports to it, so OTel spans plus the OpenInference attribute conventions make the backend an environment variable — Langfuse today, Phoenix or your existing APM tomorrow. Vendor SDK calls scattered through the agent loop make it a refactor you will never schedule. Bonus: an in-memory exporter makes the instrumentation unit-testable, so it cannot silently rot.",
    },
  ],
  resources: [
    { label: "Fly.io docs", url: "https://fly.io/docs" },
    { label: "Render docs", url: "https://render.com/docs" },
    {
      label: "GitHub Actions — required status checks",
      url: "https://docs.github.com/en/actions",
    },
    {
      label: "Docker — multi-stage builds",
      url: "https://docs.docker.com/build/building/multi-stage/",
    },
    { label: "Langfuse — tracing + cost per query", url: "https://langfuse.com" },
    { label: "Ollama Docker image", url: "https://hub.docker.com/r/ollama/ollama" },
    {
      label: "OpenTelemetry Python — tracing SDK",
      url: "https://opentelemetry.io/docs/languages/python/",
    },
    {
      label: "OpenInference — semantic conventions for LLM spans",
      url: "https://github.com/Arize-ai/openinference",
    },
    { label: "Arize Phoenix — OSS, reads OpenInference", url: "https://arize.com/docs/phoenix" },
    { label: "vLLM docs — PagedAttention & continuous batching", url: "https://docs.vllm.ai" },
    {
      label: "Anthropic — prompt caching (rung 1 of the ladder)",
      url: "https://platform.claude.com/docs/en/build-with-claude/prompt-caching",
    },
  ],
};
