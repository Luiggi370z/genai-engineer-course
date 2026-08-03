import type { PhaseContent } from "../types";

// `id` is a stable storage key, not a phase number — the number comes from the
// order in phases/index.ts, so inserting a phase never breaks saved progress.
export const memory: PhaseContent = {
  id: "p-memory",
  weeks: "Weeks 10–11",
  accent: { light: "#0E6F67", dark: "#19AA9F" },
  title: "Agents That Remember & Collaborate",
  tagline:
    "Your agent from the last phase wakes up with amnesia every session and does every job itself. This phase gives it a memory you can invalidate, a context window you spend on purpose, and workers it can delegate to — at a cost you can defend.",
  tldr: "Four memory types behind one interface, a context window spent against a hard token budget — keep, compress, evict, park — and provenance on every remembered claim so stale facts are findable. Then a supervisor delegating to tiered workers, priced against a baseline.",
  objectives: [
    {
      id: "p-memory-o1",
      text: "**Implement** the four memory types behind one interface — and say which type a given fact belongs in",
    },
    {
      id: "p-memory-o2",
      text: "**Engineer** a context window under a hard token budget: keep, compress, evict, park",
    },
    {
      id: "p-memory-o3",
      text: "**Diagnose** memory-specific failures — stale facts, context poisoning, summary drift — using provenance on every remembered claim",
    },
    {
      id: "p-memory-o4",
      text: "**Orchestrate** a supervisor and workers with tiered models, and measure the cost delta against a single-model baseline",
    },
    {
      id: "p-memory-o5",
      text: "**Contrast** MCP with A2A, and justify renting a memory framework versus owning the interface yourself",
    },
  ],
  recall: [
    {
      id: "p-memory-r1",
      q: "Why does a step cap belong in code rather than in the system prompt? Answer before you scroll.",
      a: "Because a prompt is a suggestion the model weighs against everything else it has been told, so it holds on the easy runs and fails on exactly the confused, expensive ones you built it for. A `for step in range(max_steps)` cannot be reasoned with, cannot be overridden by a tool result, and cannot be jailbroken by text hiding in a retrieved document. This phase adds memory, which means the agent’s context now contains content it wrote to itself — one more input you do not fully control.",
      from: "p3-o5",
    },
    {
      id: "p-memory-r2",
      q: "From Phase 1: what does “context rot” describe, and what does it imply about filling a million-token window?",
      a: "Accuracy degrades as you stuff the context, and facts placed in the middle of a long window get attended to least. A giant window is not a retrieval strategy. That finding is the entire justification for this phase’s objective 2 — if more context were free, budgeting it would be pointless busywork instead of the core skill.",
      from: "p1-o5",
    },
    {
      id: "p-memory-r3",
      q: "You need to retrieve a fact the agent stored three weeks ago, and it is keyed by an opaque ticket number. What retrieval design does that force?",
      a: "Keyword or exact-match lookup alongside vector search, because the embedding of `TICKET-4471` carries no usable meaning. Hybrid retrieval was the Phase 2 answer and it applies unchanged to a memory store — memory is retrieval with a write path and an expiry policy, not a new subject.",
      from: "p2-o1",
    },
  ],
  concepts: [
    {
      id: "p-memory-c1",
      title: "Four kinds of memory, one interface",
      tag: "core",
      teaches: ["p-memory-o1"],
      blocks: [
        {
          kind: "p",
          text: '"Give it memory" is not a feature, it is four features that fail in different ways. A chat transcript, a lesson learned from last Tuesday, a fact about your user, and a procedure the agent got right once are four different objects with four different lifetimes. Lump them into one vector store and you get an agent that forgets your timezone but vividly recalls a tool error from March.',
        },
        {
          kind: "table",
          headers: ["Kind", "Holds", "Lives for", "The failure when you get it wrong"],
          rows: [
            [
              "**Working**",
              "This run: the task, recent turns, the last tool result",
              "One session",
              "Overflow. The window fills and the earliest instruction silently falls out",
            ],
            [
              "**Episodic**",
              "Specific past events — *what happened, when, how it went*",
              "Until it stops being relevant",
              "A one-off incident gets treated as a rule forever",
            ],
            [
              "**Semantic**",
              "Durable facts about the user and the world (timezone, who “the team” is)",
              "Until superseded",
              "**Staleness.** The fact was true when learned and nobody wrote the expiry",
            ],
            [
              "**Procedural**",
              "How to do a job well — repaired prompts, tool recipes, hard-won constraints",
              "Until the tool changes",
              "It drifts into a second, unversioned system prompt nobody reviews",
            ],
          ],
        },
        {
          kind: "callout",
          tone: "tip",
          title: "You already built most of this in Phase 2",
          text: "Recall is retrieval: embed, search, rerank, cite. Reuse the stack you already have instead of adopting a framework to do it. What memory adds on top of retrieval is the **write path** — deciding what is worth keeping, attaching provenance, and being able to invalidate a fact later. Those three are where the engineering actually lives.",
        },
        {
          kind: "code",
          title: "One interface, four namespaces",
          code: `class MemoryStore(Protocol):
    def write(self, kind: Kind, text: str, *, source: str, ttl_days: int | None) -> str: ...
    def recall(self, kind: Kind, query: str, k: int = 5) -> list[Memory]: ...
    def forget(self, memory_id: str) -> None: ...      # invalidation is a FEATURE

@dataclass(frozen=True)
class Memory:
    id: str
    kind: Kind          # "working" | "episodic" | "semantic" | "procedural"
    text: str
    source: str         # WHERE this claim came from — a turn id, a tool call, a doc
    written_at: datetime
    expires_at: datetime | None

# One store, namespaced per (user, kind). Two reasons, both boring and vital:
#   - a semantic query must never surface another user's fact
#   - "forget everything I told you about X" has to be one deletable namespace`,
        },
        {
          kind: "list",
          items: [
            "**Write less than you think.** Every remembered sentence is a permanent tax on recall precision. If it would not change a future answer, do not store it.",
            "**Every memory carries its source.** Without provenance you cannot audit a wrong answer, and you cannot delete the one bad fact that caused it.",
            "**A live tool result beats a remembered fact, always.** Memory answers *who is the user*, never *what is the current balance* — that distinction prevents a whole family of confidently-stale answers.",
            "**Recall is a retrieval problem, so evaluate it like one.** These are golden-set rows in the Phase 3 suite: given this history, does the right fact come back in the top *k*?",
          ],
        },
      ],
    },
    {
      id: "p-memory-c2",
      title: "The window is a budget, not a bag",
      tag: "context engineering",
      teaches: ["p-memory-o2", "p-memory-o3"],
      blocks: [
        {
          kind: "predict",
          prompt:
            "Your agent loses track of an instruction given at step 2 by the time it reaches step 14. You move to a model with a **1M-token window**, so nothing has to be dropped any more — the entire history fits with room to spare. Does the step-14 behaviour get better, get worse, or stay about the same? Commit before reading on.",
          answer:
            "It usually gets *worse*, and the cost goes up while it does. Two effects compound: retrieval accuracy inside a long context degrades as you fill it, and material sitting in the middle of a long window is attended to least — the step-2 instruction is now buried under twelve steps of tool output instead of being summarized alongside it. You also pay for every one of those tokens on every subsequent call.",
          consolidation:
            "The instinct being corrected here is that context is storage. It is not: it is the model’s working attention, and adding room does not add focus. Which is why the four moves in this card are ordered the way they are — *keep* the few things that must be verbatim, *compress* what only needs its conclusion, *evict* what is finished, *park* the rest in a store you can retrieve from later. A 1M window is genuinely useful, but as headroom that lets you stop panicking about overflow, not as a substitute for deciding what deserves the tokens.",
        },
        {
          kind: "p",
          text: "A long-running agent does not fail because the model is weak; it fails because by step twelve the window is a landfill of stale tool output and the actual instruction is buried. Context engineering is the discipline of deciding, at **every** step, what deserves the tokens. Four moves, and the whole skill is knowing which one applies.",
        },
        {
          kind: "flow",
          title: "The four moves, in priority order",
          nodes: [
            { label: "Keep", sub: "constraints, the task, the last result" },
            { label: "Compress", sub: "old turns → a summary you tested" },
            { label: "Evict", sub: "superseded facts, dead branches" },
            { label: "Park", sub: "bulk text → the store, recall on demand" },
          ],
        },
        {
          kind: "table",
          headers: ["Move", "Apply it to", "The price you pay"],
          rows: [
            [
              "**Keep** (pin)",
              "Guardrails, the goal, the current step's inputs",
              "Tokens on every single turn — so pin sparingly and deliberately",
            ],
            [
              "**Compress**",
              "Long tool output, turns you have finished with",
              "It is lossy. Summary drift is a real bug and it needs a real test",
            ],
            [
              "**Evict**",
              "Facts a newer fact replaced, abandoned plans, failed retries",
              "Unrecoverable unless you parked it first",
            ],
            [
              "**Park**",
              "Documents, transcripts, anything bulky and occasionally needed",
              "A recall round-trip, plus the risk of the miss",
            ],
          ],
        },
        {
          kind: "callout",
          tone: "fix",
          title: "Context poisoning: the bug that compounds",
          text: "One wrong claim enters the running summary — a hallucinated order number, a tool error read as a fact — and every later step inherits it, restates it, and reinforces it. Prompting harder does not fix this. **Provenance does:** if every line in the assembled context names its source, a bad answer is traceable to the line that caused it, and that line is deletable. Compression is where poison enters most often, because a summary launders a guess into a statement.",
        },
        {
          kind: "code",
          title: "Assembly under a hard budget",
          code: `def assemble(task: str, pinned: list[Memory], candidates: list[Memory],
             budget_tokens: int, count: Callable[[str], int]) -> Context:
    used = count(task) + sum(count(m.text) for m in pinned)
    if used > budget_tokens:
        raise BudgetError("pinned content alone exceeds the budget")  # a design bug,
                                                                     # not a runtime one
    kept = list(pinned)
    for m in rank(candidates):            # most relevant first, dedup'd
        cost = count(m.text)
        if used + cost > budget_tokens:
            continue                      # skip, don't truncate mid-fact
        kept.append(m); used += cost
    return Context(lines=kept, tokens=used, sources=[m.source for m in kept])

# The invariant worth a test: assemble() NEVER returns more than budget_tokens,
# and a pinned line is never the thing that gets dropped.`,
        },
        {
          kind: "list",
          items: [
            "**Count tokens, do not eyeball them.** You already built a meter in Phase 1 — the budget check is that meter used in anger.",
            "**Truncating mid-fact is worse than dropping the fact.** Half a sentence reads as a whole one to the model.",
            "**Test the summarizer as a component.** Feed it a transcript with three facts and assert all three survive; drift is invisible until it is expensive.",
            "**Report the budget.** Log tokens used, lines kept, lines parked. Long-run rot is obvious in that log and invisible in the final answer.",
          ],
        },
      ],
    },
    {
      id: "p-memory-c3",
      title: "Supervisor, workers, and the cost ladder",
      tag: "cost + orchestration",
      teaches: ["p-memory-o4"],
      blocks: [
        {
          kind: "callout",
          tone: "warn",
          title: "Do not reach for a crew first",
          text: "Multi-agent systems fail in a specific way: each agent holds a different slice of the context, so they duplicate work, contradict each other, and no single trace explains the outcome. The honest default is **one agent with a better toolbox**. Split only when you can name the reason out loud — genuinely parallel work, a context too big for one window, or a step that needs a different model tier.",
        },
        {
          kind: "table",
          headers: ["Shape", "Reach for it when", "What breaks first"],
          rows: [
            [
              "**Single agent + tools**",
              "Almost always. One trace, one context, one thing to debug",
              "The window, on genuinely large jobs",
            ],
            [
              "**Supervisor + workers**",
              "Sub-tasks are independent and each worker's output is small",
              "The hand-off: workers miss context the supervisor never passed",
            ],
            [
              "**Parallel fan-out**",
              "N of the same job (summarize 20 docs) with no shared state",
              "Cost, and merging N partly-contradictory results",
            ],
            [
              "**Hierarchical crews**",
              "Rarely, and only once the flat version is measurably the bottleneck",
              "Observability — nobody can say why it did that",
            ],
          ],
        },
        {
          kind: "flow",
          title: "The cost ladder: match brainpower to difficulty, node by node",
          nodes: [
            { label: "Free: your laptop", sub: "qwen3.5:9b — route, classify, redact" },
            { label: "Cheap hosted", sub: "Haiku 4.5 / Flash-Lite — scoped work" },
            { label: "Frontier", sub: "Opus 4.8 / GPT-5.5 — planning & synthesis" },
          ],
        },
        {
          kind: "callout",
          tone: "fix",
          title: "The expensive-router myth, busted",
          text: "A popular diagram routes with the priciest model and lets cheap models do the work. Backwards for most traffic: **triage is the easy part — do it cheap**, even free on your laptop, and escalate only the hard minority. Flip it only when the *planning* is what is hard: strong orchestrator, cheap workers. One principle either way — brainpower matched to task difficulty, per node. Because your Phase-1 client is provider-agnostic, every rung is a config string.",
        },
        {
          kind: "code",
          title: "Tiering, with the receipt",
          code: `def route(task: Task) -> str:
    if task.kind == "triage":     return "local"      # $0, on your machine
    if task.difficulty == "easy": return "cheap"
    return "frontier"                                  # the minority that earns it

def run(tasks: list[Task], route=route) -> Run:
    calls = [invoke(t, tier=route(t)) for t in tasks]
    return Run(calls=calls, cost=sum(c.cost for c in calls))

# The deliverable is a comparison on YOUR task mix, not a number from a blog post:
#   baseline = run(tasks, route=lambda _: "frontier")
#   tiered   = run(tasks)
#   assert quality(tiered) >= quality(baseline) - tolerance   # from your Phase-3 κ
#   print(f"saved {1 - tiered.cost / baseline.cost:.0%} at equal quality")`,
        },
        {
          kind: "list",
          items: [
            "**Cost per run is a first-class metric.** Log it per node and per tier, or the savings claim is a vibe.",
            "**A cheaper tier is only cheaper if quality holds.** Prove it on the Phase 3 suite; a cost win with an eval regression is just a quality cut you did not admit to.",
            "**Judge the trajectory, not only the answer.** A supervisor that quietly does the workers' jobs itself passes every output check and defeats the entire design — assert that delegation actually happened.",
          ],
        },
      ],
    },
    {
      id: "p-memory-c4",
      title: "A2A vs MCP: two different questions",
      tag: "protocols",
      teaches: ["p-memory-o5"],
      blocks: [
        {
          kind: "p",
          text: "These get pitched as rivals because both are protocols with agents in the pitch deck. They answer different questions. **MCP** is how one agent reaches a *capability* — a tool, a resource, a prompt. **A2A** is how one agent asks *another agent* to own a task and report back. You will use MCP heavily in the next phase; A2A is a spec to read now and adopt when a second team's agent is genuinely on the other side of the wire.",
        },
        {
          kind: "table",
          headers: ["Dimension", "MCP", "A2A"],
          rows: [
            [
              "Question it answers",
              "How does my agent use that capability?",
              "Who else can own this task?",
            ],
            [
              "The other end is",
              "A server exposing tools, resources, prompts",
              "Another agent with its own loop and models",
            ],
            [
              "Unit of exchange",
              "A tool call and its result",
              "A task, its status, and the artifacts it produced",
            ],
            [
              "Discovery",
              "List what the server exposes",
              "An agent card describing skills and endpoints",
            ],
            [
              "Reach for it when",
              "Anything your agent should be able to *do*",
              "The work belongs to a team or vendor you do not control",
            ],
          ],
        },
        {
          kind: "callout",
          tone: "tip",
          title: "What to actually do this week",
          text: "For your own crew, delegate **in process** — a function call is cheaper, faster and infinitely easier to debug than a protocol hop, and it keeps one trace. Expose capabilities over MCP so anything can consume them. Read the A2A spec so you can hold the comparison in an interview, and reach for it the day the agent on the other side stops being yours.",
        },
      ],
    },
    {
      id: "p-memory-c5",
      title: "Own the interface, rent the implementation",
      tag: "frameworks",
      teaches: ["p-memory-o5"],
      blocks: [
        {
          kind: "p",
          text: "Memory frameworks are moving fast and consolidating faster. That is a bad reason to avoid them and an excellent reason to keep them behind your own interface: your agent depends on the `MemoryStore` protocol from the first card, and a framework is one adapter that satisfies it. Swapping vendors becomes a file, not a project.",
        },
        {
          kind: "table",
          headers: ["Option", "Mental model", "Good when", "Watch out"],
          rows: [
            [
              "**Roll your own**",
              "Your Phase-2 retrieval stack plus a write path",
              "You want to understand it, and your needs are one namespace deep",
              "You will write the boring parts: dedup, invalidation, decay",
            ],
            [
              "**Mem0**",
              "A memory *service*: add turns, it extracts and consolidates facts",
              "You want extraction and conflict resolution handed to you",
              "It runs an LLM on the write path — budget and pin it like any judge",
            ],
            [
              "**LangMem**",
              "Typed memory schemas over the LangGraph store",
              "You are already on LangGraph and want its store with extraction on top",
              "Thin layer, slow release cadence — check the last release date yourself",
            ],
            [
              "**Letta**",
              "The agent owns its own memory and edits it as a tool",
              "Long-lived companions where self-editing memory is the point",
              "Opinionated: you adopt its agent model, not just a store",
            ],
            [
              "**Zep / Graphiti**",
              "A temporal knowledge graph — facts with validity intervals",
              "*When* something became true matters as much as what",
              "A graph is a second data model to operate and reason about",
            ],
          ],
        },
        {
          kind: "callout",
          tone: "warn",
          title: "Adopt on evidence, not on stars",
          text: "Before any memory dependency: check the last release date, read what it does on the **write** path (an LLM call you did not budget for?), and confirm you can export your data. A thin wrapper over a store you could use directly is worth very little; the store underneath is usually the durable part. Write that judgement down in the repo — future-you will not remember why.",
        },
        {
          kind: "code",
          title: "The pattern that makes the choice reversible",
          code: `# One contract suite, parameterised over every adapter you ship.
@pytest.fixture(params=["fake", "mem0", "langmem"])
def store(request) -> MemoryStore:
    return build_store(request.param)          # fake runs offline, in CI

def test_a_written_fact_is_recallable(store: MemoryStore):
    store.write("semantic", "Lu works in UTC-5", source="turn-3", ttl_days=None)
    assert "UTC-5" in " ".join(m.text for m in store.recall("semantic", "timezone"))

def test_forget_actually_forgets(store: MemoryStore):
    mid = store.write("semantic", "manager is Dana", source="turn-9", ttl_days=None)
    store.forget(mid)
    assert store.recall("semantic", "who is my manager") == []

# Adapters come and go; these tests are the thing you actually own.`,
        },
      ],
    },
  ],
  example: {
    title: "Field story: the assistant that would not let Dana go",
    text: "An assistant learned a perfectly true fact from an early conversation — Dana is the user's manager, CC her on anything about budget — and stored it with no source and no expiry. Dana changed teams two months later. The user said so, in a session whose transcript was summarized and dropped; the *new* manager's name never made it into the durable store, and the old fact was never contradicted, only outranked occasionally. For weeks the assistant kept quietly adding Dana to budget threads, and because every remembered claim looked identical in the prompt, nobody could tell which line was responsible. The fix was not a better model. It was provenance and an expiry on every semantic write, plus a rule that a memory the user corrects gets deleted, not merely outvoted.",
  },
  exercises: [
    {
      id: "p-memory-e1",
      title: "Four memory types behind one interface",
      repo: "phase5-memory/01-memory-types",
      effort: { fast: 75, integration: 20, realistic: 120 },
      rung: "faded",
      proves: "implement",
      task: "Implement `write`, `recall` and `forget` over four namespaces on the retrieval stack you already know. Then prove the types stay separated: a procedural recipe must never come back as the answer to a semantic question about the user, and a forgotten fact must be gone — not merely outranked.",
      assesses: ["p-memory-o1"],
      needs: ["p2-o1"],
      solution: [
        "Namespace by `(user, kind)`. That one decision gives you type separation, per-user isolation, and a deletable unit for “forget everything about X” — all for free.",
        "Store `source` and `expires_at` on every row from the very first commit. Retrofitting provenance means re-labeling everything you already wrote.",
        "Test `forget` by asserting an empty recall, not a lower rank. A “deleted” fact that still ranks second is still going to end up in a prompt.",
      ],
      code: `# src/memory.py — one store, four namespaces
class VectorMemory:
    def __init__(self, embed: Embedder, client: QdrantClient | None = None) -> None:
        self.client = client or QdrantClient(":memory:")   # same API as prod
        self.embed = embed

    def write(self, kind: Kind, text: str, *, source: str,
              ttl_days: int | None = None) -> str:
        mid = str(uuid4())
        self.client.upsert(self._ns(kind), points=[PointStruct(
            id=mid, vector=self.embed(text),
            payload={"text": text, "source": source, "kind": kind,
                     "expires_at": _expiry(ttl_days)})])
        return mid

    def recall(self, kind: Kind, query: str, k: int = 5) -> list[Memory]:
        hits = self.client.query_points(self._ns(kind), query=self.embed(query),
                                        limit=k).points
        return [_to_memory(h) for h in hits if not _expired(h)]

# tests/test_memory.py — offline, deterministic fake embedder
def test_procedural_memory_never_answers_a_semantic_question(store):
    store.write("procedural", "retry the calendar tool once on 429", source="run-2")
    store.write("semantic", "Lu works in UTC-5", source="turn-3")
    assert [m.kind for m in store.recall("semantic", "what timezone?")] == ["semantic"]`,
    },
    {
      id: "p-memory-e2",
      title: "Spend the window on purpose",
      repo: "phase5-memory/02-context-engineering",
      effort: { fast: 60, integration: 20, realistic: 100 },
      rung: "faded",
      proves: "implement",
      task: "Build a context assembler with a hard token budget and the four moves: pin the constraints, compress old turns, evict superseded facts, park the bulk. Then plant a poisoned fact in a transcript and show you can trace it to its source and remove it.",
      assesses: ["p-memory-o2", "p-memory-o3"],
      solution: [
        "Make exceeding the budget impossible by construction, and make pinned-content-over-budget a loud error at assembly time — it is a design bug, not a runtime hiccup.",
        "Skip a line that does not fit rather than truncating it. A half-fact reads as a whole fact to the model.",
        "Keep the source on every assembled line. That is what turns “the agent said something weird” into “line 4 came from tool call 7, delete it”.",
      ],
      code: `# The three tests that make this real
def test_never_exceeds_the_budget():
    ctx = assemble(TASK, pinned=PINS, candidates=MANY, budget_tokens=200, count=count)
    assert ctx.tokens <= 200

def test_pinned_constraints_survive_pressure():
    ctx = assemble(TASK, pinned=PINS, candidates=MANY, budget_tokens=120, count=count)
    assert all(p in ctx.lines for p in PINS)      # the leash never gets evicted

def test_a_poisoned_line_is_traceable_and_removable():
    ctx = assemble(TASK, pinned=[], candidates=[GOOD, POISON], budget_tokens=500,
                   count=count)
    bad = [m for m in ctx.lines if m.source == "tool-call-7"]
    assert bad, "provenance missing — you cannot audit what you cannot trace"
    store.forget(bad[0].id)
    assert POISON not in assemble(TASK, [], store.all(), 500, count).lines

# And the one that catches summary drift before it costs you:
def test_compression_preserves_every_hard_fact():
    summary = compress(TRANSCRIPT_WITH_THREE_FACTS, summarize=fake_summarizer)
    assert all(f in summary for f in ("INV-88231", "UTC-5", "no auto-send"))`,
    },
    {
      id: "p-memory-e3",
      title: "A crew that earns its keep (medium)",
      repo: "phase5-memory/03-supervisor-crew",
      effort: { fast: 45, integration: null, realistic: 75 },
      rung: "faded",
      proves: "integrate",
      task: "Build a supervisor that delegates to two workers with tiered models, and account for cost per node. Run the same task list single-tier and tiered, then report the cost delta with quality held constant. Add the trajectory assertion that the supervisor actually delegated instead of doing the work itself.",
      assesses: ["p-memory-o4"],
      needs: ["p1-o2", "p3-o5"],
      solution: [
        "The cost delta is the deliverable, and it is *your* number on *your* task mix — not a figure from a blog post. Report it next to the eval score or it means nothing.",
        "Route on task difficulty, not on task importance. Triage is cheap work; synthesis is what earns the frontier model.",
        "Assert the trajectory: a supervisor that silently answers everything itself passes every output check while defeating the whole design.",
      ],
      code: `# tests/test_crew.py — no models, all deterministic
def test_tiering_is_cheaper_at_equal_quality():
    baseline = run(TASKS, route=lambda _: "frontier")
    tiered = run(TASKS)
    assert quality(tiered) >= quality(baseline)      # same answers on this mix
    assert tiered.cost < baseline.cost

def test_the_supervisor_actually_delegates():
    trace = run(TASKS).trace
    assert {c.agent for c in trace if c.agent != "supervisor"} == {"researcher", "writer"}
    assert not any(c.agent == "supervisor" and c.kind == "research" for c in trace)

def test_a_worker_failure_does_not_sink_the_run():
    out = run(TASKS, workers={"researcher": exploding_worker})
    assert out.status == "partial" and out.errors      # error-as-data, not a crash`,
    },
    {
      id: "p-memory-e4",
      title: "Rent two implementations, keep your interface",
      repo: "phase5-memory/04-memory-frameworks",
      effort: { fast: 60, integration: 25, realistic: 100 },
      rung: "faded",
      proves: "integrate",
      task: "Implement your `MemoryStore` protocol twice — once on Mem0, once on LangMem — and run one shared contract suite against both plus an offline fake. Then write the one-paragraph adoption verdict: which you would ship, and what would make you change your mind.",
      assesses: ["p-memory-o1", "p-memory-o5"],
      solution: [
        "Parameterise the contract suite over adapters. The fake keeps the fast tier offline; the real adapters run in the integration tier against a local model.",
        "Read what each framework does on the *write* path. An LLM call hidden inside `add()` is a cost and latency surprise you should discover here, not in production.",
        "Check the last release date of anything you are about to depend on, and record the version you verified in the lesson's `VERIFIED.md`. That habit is the whole reason this course still runs.",
      ],
      code: `# src/adapters.py — same protocol, two rented backends
class Mem0Store:                       # mem0ai 2.x
    def __init__(self, config: dict) -> None:
        self.m = Memory.from_config(config)          # ollama llm + embedder, local qdrant

    def write(self, kind: Kind, text: str, *, source: str, ttl_days=None) -> str:
        return self.m.add(text, user_id=self._ns(kind), metadata={"source": source})

    def recall(self, kind: Kind, query: str, k: int = 5) -> list[Memory]:
        # 2.x moved entity ids into \`filters\`; the old user_id= kwarg is 1.x
        hits = self.m.search(query, filters={"user_id": self._ns(kind)}, limit=k)
        return [_to_memory(h) for h in hits["results"]]

class LangMemStore:                    # langmem over a LangGraph store
    def __init__(self, store: BaseStore, model: str) -> None:
        self.manager = create_memory_store_manager(
            model, namespace=("memories", "{kind}"), schemas=[Fact],
            enable_inserts=True, enable_deletes=True)

# tests/test_contract.py runs the SAME assertions against fake | mem0 | langmem`,
    },
    {
      id: "p-memory-e5",
      title: "Blank editor: a token budget you cannot cheat",
      rung: "independent",
      proves: "implement",
      task: "Empty directory, no scaffold. Write `fit(messages, budget)` from nothing: it takes a long transcript and a hard token limit and returns what actually goes in the window, applying keep, compress, evict and park in that order. Count real tokens, not characters. Then write the test that matters — feed it a transcript containing three facts you know are load-bearing, squeeze the budget until compression has to fire, and assert all three survive. Finish by printing tokens used, lines parked, and which move dropped what.",
      assesses: ["p-memory-o2", "p-memory-o3"],
      needs: ["p1-o2"],
      solution: [
        "You counted tokens with a real tokenizer. Dividing characters by four is the estimate Phase 1 spent a whole card teaching you to distrust, and a budget built on it silently overflows on code and non-English text.",
        "The pinned material is selected before anything else competes for room, and if the pins alone exceed the budget your function says so loudly instead of quietly trimming them. A context engineer who truncates the instruction has optimized the wrong thing.",
        "Ranked material that does not fit is skipped whole rather than cut mid-fact. Half a fact is worse than no fact: it reads as authoritative and is wrong.",
        "Your fact-survival test genuinely fails when you weaken the summarizer. If it passes no matter what you do to the compression step, you have written a test that only checks the function returns a string.",
        "Every parked or compressed line keeps its source. Provenance is what turns “the agent said something false” into “row 41, written on the 3rd, from this transcript” — and it is unretrofittable, which is why the rubric asks for it on the first version rather than the second.",
        "You can name which of the four moves you would reach for first on a real 30k-into-8k problem, and why *park* is not the answer to everything. Getting to that judgement is the point; the function is just the thing that forced you to have it.",
      ],
    },
  ],
  checkpoint: [
    {
      id: "p-memory-q1",
      q: "Your agent confidently tells a user something that was true last quarter. Which memory type failed, and what was missing?",
      a: "Semantic memory — the durable facts store. What was missing is an expiry and a correction path: the fact was written with no `expires_at`, so nothing ever retired it, and when the user supplied the new value the old row was outranked rather than deleted. Provenance is the other half; without a source on the claim you cannot find the row that caused the answer. Facts that change on their own belong behind a live tool call, not in memory.",
      demands: ["evidence", "failure-modes"],
    },
    {
      id: "p-memory-q2",
      q: "You have 8k tokens of context budget and 30k of potentially relevant material. Walk through your decision.",
      a: "Pin first: the task and the hard constraints, and if those alone blow the budget, that is a design bug to fix now. Then rank the rest by relevance and fill what fits, skipping anything that does not rather than truncating it mid-fact. Compress finished turns into a summary you have tested for fact survival. Evict anything a newer fact supersedes. Park the bulk in the store and recall on demand. Then log tokens used and lines parked, because long-run rot shows up in that log long before it shows up in an answer.",
      demands: ["alternatives", "constraints", "evidence"],
    },
    {
      id: "p-memory-q3",
      q: "Why is “add a summarizer” not a safe answer to a full context window?",
      a: "Because compression is a lossy write that launders guesses into statements. A summary can drop the one constraint that mattered, and it can absorb a hallucinated or misread detail and hand it to every later step as established fact — that is context poisoning, and it compounds. Treat the summarizer as a component with tests: feed it a transcript with known hard facts and assert they survive, and keep the source on each line so a poisoned claim stays traceable and deletable.",
      demands: ["evidence", "failure-modes"],
    },
    {
      id: "p-memory-q4",
      q: "When is a supervisor-plus-workers design the wrong call?",
      a: "Whenever you cannot name what it buys. Splitting the job splits the context: workers miss what the supervisor never passed, results contradict each other, and no single trace explains the outcome. The default is one agent with a better toolbox; a crew earns its complexity only for genuinely parallel sub-tasks, a job too large for one window, or a step that wants a different model tier. And if you do split, assert delegation actually happens — a supervisor doing the work itself passes every output check while wasting the whole design.",
      demands: ["alternatives", "constraints", "failure-modes"],
    },
    {
      id: "p-memory-q5",
      q: "An interviewer asks whether you would use MCP or A2A for your agents. What is the right answer?",
      a: "That they answer different questions. MCP connects an agent to a capability — tools, resources, prompts — and is the right port for anything your agent should be able to do. A2A hands a whole task to another agent that has its own loop and models, and pays off when that agent belongs to a team or vendor you do not control. For your own crew, delegate in process: a function call is cheaper, faster, and keeps one debuggable trace. Expose your capabilities over MCP, and reach for A2A the day the other side stops being yours.",
      demands: ["alternatives", "constraints"],
    },
  ],
  workshop: {
    id: "w-memory",
    title: "Workshop · The assistant that remembers you",
    subtitle:
      "Give the assistant a memory it can invalidate, a context budget it respects, and a research crew it delegates to — with the cost written down.",
    repo: "workshops/assistant",
    doc: "WORKSHOP-MEMORY-CREW.md",
    effort: { fast: 180, integration: 30, realistic: 360 },
    proves: "integrate",
    assesses: ["p-memory-o1", "p-memory-o2", "p-memory-o3", "p-memory-o4"],
    needs: ["p3-o2", "p-evals-o5"],
    blocks: [
      {
        kind: "p",
        text: "The assistant currently starts every session as a stranger and does every job on the frontier model. This workshop adds the two capabilities that make it feel like software rather than a demo: **memory with an expiry date**, and **delegation with a receipt**. Both plug into the eval layer you built in Phase 3 — recall becomes golden-set rows, and the cost comparison sits next to the quality score instead of replacing it.",
      },
      {
        kind: "callout",
        tone: "tip",
        title: "Memory is the feature users notice",
        text: '"It remembered" is the single most convincing thing a personal assistant can do, and "it remembered something wrong and would not let go" is the fastest way to lose that trust. Build the `forget` path in the same commit as the `write` path — not in a follow-up you will never get to.',
      },
      {
        kind: "flow",
        title: "The layer you're adding",
        nodes: [
          { label: "Write path", sub: "extract → source + TTL → namespace" },
          { label: "Recall", sub: "top-k per kind, expired rows skipped" },
          { label: "Assemble", sub: "pin · compress · evict · park" },
          { label: "Crew", sub: "supervisor → tiered workers" },
          { label: "Receipt", sub: "tokens, cost, eval score" },
        ],
      },
      {
        kind: "code",
        title: "The seam you implement",
        code: `# before/src/assistant/memory.py
def remember(store: MemoryStore, turn: str) -> list[str]:
    # TODO: decide what in this turn is worth keeping AT ALL
    # TODO: classify it (working | episodic | semantic | procedural)
    # TODO: write with source + ttl; return the ids you created
    ...

def context_for(store: MemoryStore, task: str, budget_tokens: int) -> Context:
    # TODO: pin the constraints, recall per kind, fill to the budget, never exceed it
    ...

# before/src/assistant/crew.py
def delegate(task: str, workers: dict[str, Worker], route: Router) -> CrewRun:
    # TODO: supervisor plans, workers execute on their tier, results merge
    # TODO: record cost per node — the receipt IS the deliverable
    ...`,
      },
      {
        kind: "callout",
        tone: "warn",
        title: "Prove the savings on your own suite",
        text: "A tiered crew that is 40% cheaper and two points worse on your Phase-3 gate is not a win, it is an undeclared quality cut. Run the eval suite both ways and report cost **and** score together. If the cheap tier holds up, you have a number you can defend in an interview — and it is yours, measured on your task mix.",
      },
    ],
    deliverables: [
      {
        id: "w-memory-d1",
        text: "Memory writes carry a **source and a TTL**, and `forget` makes a fact unrecallable — proven by a test, not by inspection",
        tier: "minimum",
      },
      {
        id: "w-memory-d2",
        text: "The assistant recalls a fact you told it in a **previous session** and cites where it learned it",
        tier: "minimum",
      },
      {
        id: "w-memory-d3",
        text: "Context assembly respects a **hard token budget**, pins the guardrails, and logs tokens used vs. parked",
        tier: "full",
      },
      {
        id: "w-memory-d4",
        text: "A **corrected** fact replaces the old one — the stale row is deleted, not merely outranked",
        tier: "full",
      },
      {
        id: "w-memory-d5",
        text: "A supervisor delegates research to **tiered workers**; a test asserts the delegation actually happened",
        tier: "full",
      },
      {
        id: "w-memory-d6",
        text: "`make eval` reports **cost per run alongside the quality score**, single-tier vs. tiered, on the Phase-3 suite",
        tier: "full",
      },
    ],
    stretch: [
      "Add recall rows to the golden set — “given this history, does the right fact come back?” — and gate on them like any other slice.",
      "Add memory decay: episodic rows lose weight with age unless re-confirmed, and write the note explaining the half-life you chose.",
      "Swap your hand-rolled store for a framework adapter behind the same protocol, run the identical contract suite, and record the verdict in the repo.",
    ],
  },
  resources: [
    {
      label: "LangGraph — memory concepts (short- vs long-term)",
      url: "https://langchain-ai.github.io/langgraph/concepts/memory/",
    },
    {
      label: "LangGraph store reference (BaseStore)",
      url: "https://langchain-ai.github.io/langgraph/reference/store/",
    },
    { label: "LangMem docs", url: "https://langchain-ai.github.io/langmem/" },
    { label: "Mem0 docs (open-source path)", url: "https://docs.mem0.ai" },
    { label: "Letta docs (self-editing memory)", url: "https://docs.letta.com" },
    {
      label: "Graphiti — temporal knowledge graphs (Zep)",
      url: "https://github.com/getzep/graphiti",
    },
    {
      label: "Anthropic — effective context engineering for AI agents",
      url: "https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents",
    },
    {
      label: "Cognition — don’t build multi-agents",
      url: "https://cognition.ai/blog/dont-build-multi-agents",
    },
    {
      label: "MemGPT paper (the origin of self-editing memory)",
      url: "https://arxiv.org/abs/2310.08560",
    },
    { label: "A2A protocol spec", url: "https://a2a-protocol.org" },
  ],
};
