// Generated from the shipped course bundle by scripts/extract-data.mjs.
// Edit freely from here on — this file is the source of truth for the content.

import type { PhaseContent } from "../types";

export const agents: PhaseContent = {
  id: "p3",
  weeks: "Weeks 7–9",
  accent: { light: "#7631EC", dark: "#AB85ED" },
  title: "Agents on a Leash",
  tagline:
    'Build an agent from scratch, understand every moving part, then learn which framework to reach for and when. This is the phase that turns "I call an API" into "I ship autonomous systems."',
  tldr: "You write the reason–act–observe loop yourself before touching a framework, build tools that validate and return errors as data, and put irreversible actions behind an approval that lives in code, never the prompt. Then LangGraph, Pydantic AI and CrewAI head to head.",
  objectives: [
    {
      id: "p3-o1",
      text: "**Implement** the reason–act–observe loop from scratch, no framework — and define what an agent actually is",
    },
    {
      id: "p3-o2",
      text: "**Build** a **tool** properly — schema, docstring-as-interface, validation, errors as data. Every connection to the outside world is a tool",
    },
    {
      id: "p3-o3",
      text: "**Implement** **human-in-the-loop (HITL)** approval for anything irreversible, and explain why the leash lives in code and never in the prompt",
    },
    {
      id: "p3-o4",
      text: "**Compare** LangGraph, Pydantic AI and CrewAI hands-on, then **justify** one for a given job",
    },
    {
      id: "p3-o5",
      text: "**Contain** an agent in code — hard step caps, wall-clock deadlines, least-privilege tools — so a bad run stays cheap",
    },
  ],
  recall: [
    {
      id: "p3-r1",
      q: "Cold: what does a reranker do that hybrid search cannot, and why is it worth a second model call?",
      a: "Hybrid search scores every document independently against the query, which is why it can go wide cheaply. A reranker is a cross-encoder — it reads the query and one candidate *together*, so it can judge relevance in context rather than by vector proximity. You fetch 20–150 wide, then rerank down to 3–5. It matters here because an agent that searches is going to make that call in a loop, and a loop is where a sloppy retrieval step turns into a sloppy bill.",
      from: "p2-o1",
    },
    {
      id: "p3-r2",
      q: "Name the four ways an LLM judge lies to you. Get as many as you can before you check.",
      a: "Position bias (it prefers whichever answer came first), verbosity bias (longer reads as better), self-preference (it favours text from its own family), and miscalibration (its confidence has no relationship to its accuracy). This is about to matter more, not less: you are going to build agents that call a model to decide what to do next, and every one of those biases now sits inside a control-flow decision instead of a score in a report.",
      from: "p-evals-o2",
    },
    {
      id: "p3-r3",
      q: "Why does an eval suite need unanswerable questions, and what would you fail to notice without them?",
      a: "They are the only test of the abstention path — the system’s ability to say “not in the docs.” Without them every row is answerable by construction, so a model that has learned to always produce something confident scores perfectly. The agent equivalent, coming up in this phase, is worse: an agent with no “I cannot do this” branch does not abstain, it starts inventing tool calls.",
      from: "p-evals-o1",
    },
  ],
  concepts: [
    {
      id: "p3-c1",
      title: "What is an agent, really?",
      tag: "fundamentals",
      teaches: ["p3-o1"],
      blocks: [
        {
          kind: "p",
          text: "Strip away the hype and an **agent** is one idea: a model in a loop that can **act on the world and see what happened**, repeating until the job is done. A plain LLM call is a vending machine — prompt in, text out, done. An agent is an intern with a phone and a to-do list: it thinks about the next step, does something (searches, calls an API, runs code), looks at the result, and decides what to do next.",
        },
        {
          kind: "flow",
          title: "The whole idea in four beats",
          nodes: [
            { label: "Reason", sub: "model picks the next move" },
            { label: "Act", sub: "YOUR code runs a tool" },
            { label: "Observe", sub: "result goes back into context" },
            { label: "Loop or finish", sub: "until done — capped in code" },
          ],
        },
        {
          kind: "list",
          items: [
            "The three ingredients: a **goal** (what to achieve), **tools** (what it can do), and a **loop** (keep going until done or stopped).",
            "The model never actually *does* anything — it only **requests** actions. Your code decides whether and how to run them. That gap is where all your control lives.",
            "This pattern is called **ReAct** (Reason + Act). Everything fancier — multi-agent, planners, graphs — is this loop with more structure.",
          ],
        },
        {
          kind: "callout",
          tone: "tip",
          title: "Why build it from scratch first",
          text: 'Frameworks hide the loop, and when your agent misbehaves you’ll be debugging a black box. Write the ~40-line version once (next card) and every framework afterward becomes "oh, that’s just the loop with checkpointing / with roles / with types." You’ll never be lost in someone else’s abstraction again.',
        },
      ],
    },
    {
      id: "p3-c2",
      title: "The loop, from scratch — with the leash",
      tag: "core",
      teaches: ["p3-o1", "p3-o5"],
      blocks: [
        {
          kind: "predict",
          prompt:
            "You are worried about runaway costs, so your system prompt ends with: *“You have a strict budget. Use at most 5 tool calls, then stop and report what you found.”* You ship it. Over a thousand real runs, what happens — does it hold, does it fail loudly, or something else? Pick one before reading on.",
          answer:
            "It mostly holds, and that is the problem. The great majority of runs stop at four or five calls, so it looks like a working control. Then a small fraction — the confusing goals, the tool that keeps returning errors, the run that is *almost* finished at step five — sail straight past it to fifteen or forty calls, because the instruction was a suggestion in a document the model is free to weigh against everything else in the prompt.",
          consolidation:
            "A control that works 97% of the time is not a control, it is a statistic, and the 3% is exactly the population you built it for: the long confused runs are the expensive ones. This is why objective 5 says *in code* — `for step in range(max_steps)` cannot be talked out of it, cannot be argued with by a clever tool result, and cannot be jailbroken by a prompt injection hiding in a retrieved document. Keep the prompt sentence if you like, since it makes the well-behaved runs shorter. Just never let it be the thing standing between you and the bill.",
        },
        {
          kind: "p",
          text: "Here is a complete agent. No framework, no magic. Read every line — this is the mental model you’ll carry into LangGraph and everything after.",
        },
        {
          kind: "code",
          title: "agent.py — the entire thing",
          code: `def run_agent(goal, tools, max_steps=8, deadline_s=60):
    state, start = [], time.monotonic()
    for step in range(max_steps):                  # HARD cap — physics, not a wish
        if time.monotonic() - start > deadline_s:
            return fail("timeout")                 # wall-clock leash
        decision = llm_decide(goal, state, tools)  # model reasons: which tool? or done?
        if decision.is_final:
            return decision.answer
        tool = tools[decision.name]                # look up the requested tool
        result = tool.run(**decision.args)         # YOUR code executes it (sandboxed)
        state.append((decision, result))           # observation feeds the next turn
    return fail("max_steps_exceeded")              # degrade gracefully, never hang`,
        },
        {
          kind: "callout",
          tone: "warn",
          title: "Rule #1: the leash lives in code, never the prompt",
          text: 'Writing "try at most 5 times" in the prompt is a polite request the model can ignore — especially once its context gets muddled. A `for` loop with a hard `break`, a wall-clock deadline, and a spend cap are **guarantees**. This single discipline is the difference between a contained failure and a 3 a.m. surprise invoice.',
        },
        {
          kind: "p",
          text: "That’s it. An agent framework’s job is to make this loop **durable** (survive a crash), **observable** (trace every step), and **composable** (many agents, shared state) — but the beating heart is always these ~12 lines.",
        },
      ],
    },
    {
      id: "p3-c3",
      title: "Tools: how an agent touches the world",
      tag: "this is the whole game",
      teaches: ["p3-o2"],
      blocks: [
        {
          kind: "p",
          text: "**Every connection to anything outside the model is a tool.** Reading email? A tool. Hitting a weather API? A tool. Querying your database, sending a Telegram message, running a Python snippet — tools, all of them. An agent is only as capable as its toolbox, so learning to write a good tool is *the* core agent skill.",
        },
        {
          kind: "p",
          text: "A tool is just a function plus a **description the model can read**. The model chooses which tool to call and fills in the arguments using **only the name, the docstring, and the type hints**. Nothing else. That means your docstring is not a comment — it is the API the model programs against.",
        },
        {
          kind: "code",
          title: "Anatomy of a good tool",
          code: `def get_weather(city: str, when: str = "today") -> dict:
    """Get the weather forecast for a city.

    Use this when the user asks about weather, temperature, or rain.
    Args:
        city: City name, e.g. "Lima" or "Tokyo".
        when: "today", "tomorrow", or an ISO date like "2026-07-20".
    Returns a dict with temp_c, condition, and chance_of_rain.
    """
    # 1. VALIDATE inputs — never trust the model's arguments blindly
    if not city.strip():
        return {"error": "city is required"}
    # 2. DO the work, with a timeout
    try:
        return weather_api.fetch(city, when, timeout=5)
    except TimeoutError:
        return {"error": "weather service slow, try again"}  # errors are DATA,
    # 3. return a shape the model can reason about  ---------- not exceptions`,
        },
        {
          kind: "list",
          items: [
            '**Name + docstring = the interface.** "get_weather" with a docstring that says *what* it does AND *when* to use it beats "wx()" with no docs every time. Write it like a prompt, because it is one.',
            "**Type hints are the schema.** They tell the model (and your validation layer) exactly what shape each argument takes. Pydantic models for anything non-trivial.",
            "**Validate every argument.** The model will occasionally hand you nonsense. Check it before you act.",
            '**Return errors as data, not exceptions.** "{"error": "city not found"}" lets the agent recover and try again; a raw crash kills the run.',
            "**One tool, one job.** Small, sharp tools compose; a mega-tool with a `mode` parameter confuses the model.",
            "**Retry with backoff inside the tool**, and cap it. An agent multiplies every flaky dependency by its step count — a tool that fails one call in fifty fails most long runs.",
          ],
        },
        {
          kind: "callout",
          tone: "tip",
          title: "The blank-docstring test",
          text: "Delete a tool’s docstring and watch the agent flail — it no longer knows what the tool is for or when to reach for it. That felt experience is the lesson: to the model, the description *is* the tool. This is also exactly how MCP tools work (Phase 7), so the skill transfers directly.",
        },
      ],
    },
    {
      id: "p3-c4",
      title: "Human-in-the-loop: the pause before it does something scary",
      tag: "HITL",
      teaches: ["p3-o3"],
      blocks: [
        {
          kind: "p",
          text: "Autonomy is great until your agent decides to delete a database, wire money, or email all your customers. **Human-in-the-loop (HITL)** means the agent stops before an irreversible or high-stakes action and waits for a person to approve. It’s the seatbelt: rarely needed, non-negotiable when it is.",
        },
        {
          kind: "flow",
          title: "Where the human sits",
          shape: "decision",
          nodes: [
            {
              label: "Agent plans a risky action — the run pauses, state saved",
              sub: "refund, delete, send. A human reads the proposed call and picks one of three:",
            },
            { label: "Approve", sub: "resume from the checkpoint, unchanged" },
            { label: "Edit, then approve", sub: "resume with the human’s arguments instead" },
            { label: "Reject", sub: "abort cleanly and say why — never silently retry" },
          ],
        },
        {
          kind: "list",
          items: [
            "**Classify actions by reversibility.** Read-only (search, fetch) → no gate. Reversible writes (draft an email) → maybe. Irreversible (send, pay, delete) → always a human.",
            '**Least privilege beats approval.** The strongest control isn’t asking permission — it’s not giving the agent a "wire money" tool at all unless it truly needs one. An action the agent can’t take can’t be tricked out of it.',
            "**HITL needs durable state.** The run might pause for hours until a human clicks approve. That’s why real frameworks checkpoint (next card) — the process can die and resume mid-pause.",
          ],
        },
        {
          kind: "callout",
          tone: "warn",
          title: "HITL is also your injection backstop",
          text: 'In Phase 6 you’ll see attackers plant instructions in the data your agent reads ("indirect prompt injection"). A human approving every irreversible action is the last line that holds even when a clever payload slips past every filter. Least privilege + HITL is the combination security researchers converged on in 2026.',
        },
      ],
    },
    {
      id: "p3-c5",
      title: "The framework shoot-out: LangGraph vs Pydantic AI vs CrewAI",
      tag: "choose well",
      teaches: ["p3-o4"],
      blocks: [
        {
          kind: "p",
          text: "You now understand the loop, so frameworks stop being mysterious — each just packages it with a different priority. Learn all three by what they optimize for, then choose by your dominant constraint, not by GitHub stars.",
        },
        {
          kind: "table",
          headers: ["Framework", "Its big idea", "Reach for it when…"],
          rows: [
            [
              "LangGraph",
              "Agents as a state machine: typed shared state, nodes, edges, and checkpointing (save points).",
              "You need durability, branching, cycles, or HITL that pauses for hours. The production default.",
            ],
            [
              "Pydantic AI",
              "Type-safe agents: everything is a validated Pydantic model, minimal ceremony, feels like normal Python.",
              "You want structure and safety without a graph. Great for a clean single agent with tools.",
            ],
            [
              "CrewAI",
              'Role-based crews: give each agent a persona ("researcher", "writer") and let them collaborate.',
              "You’re prototyping a multi-agent team fast and want readable role/task abstractions.",
            ],
          ],
        },
        {
          kind: "p",
          text: "**LangGraph** is the one to know deepest — its checkpointing is a genuine superpower. It models your agent as a graph and saves state at every node, so a crashed run resumes from the last save point, and an `interrupt()` can pause a run **indefinitely** for HITL and pick up exactly where it left off. That’s why it runs in production at Klarna, Uber, and LinkedIn.",
        },
        {
          kind: "code",
          title: "LangGraph: a save point and a human pause",
          code: `from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt

def draft(state):  return {"email": write_email(state["notes"])}
def approve(state): return {"ok": bool(interrupt("Send this email?"))}  # PAUSES here

g = StateGraph(dict)
g.add_node("draft", draft); g.add_node("approve", approve)
g.add_edge("draft", "approve"); g.add_edge("approve", END)
app = g.compile(checkpointer=MemorySaver())   # crash mid-run? resume by thread_id`,
        },
        {
          kind: "code",
          title: "Pydantic AI: same job, type-first, no graph",
          code: `from pydantic_ai import Agent

agent = Agent("claude-sonnet-4-6", system_prompt="You are an email assistant.")

@agent.tool_plain                       # a tool, validated by its type hints
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email. Use only after the user confirms."""
    return mailer.send(to, subject, body)

result = agent.run_sync("Email the team the Q3 recap")  # typed result out`,
        },
        {
          kind: "callout",
          tone: "tip",
          title: "Don’t take this recommendation — measure it",
          text: "The usual advice: default to **LangGraph** (durability and HITL are worth the graph), reach for **Pydantic AI** when one well-typed agent is enough, **CrewAI** when sketching a multi-role team. That paragraph is also every other blog post, because it is what the docs say. Exercise 4.4 makes you earn it: the *same* agent in all three, scored on six dimensions from numbers you recorded. Expect several dimensions to come back undecided — that is the honest result, and knowing which ones your test couldn’t separate is worth more than a verdict you inherited.",
        },
      ],
    },
  ],
  example: {
    title: "Field story: the agent that wouldn’t stop Googling",
    text: 'A team shipped a research agent with no step cap — just a prompt asking it to "stop when confident." One ambiguous query later it ran the same web search 40 times in a loop, each call billed, convinced the next result would be the one. A three-line `for` loop with a hard break would have caught it for free. They learned Rule #1 the expensive way: the leash lives in code. You get to learn it here instead.',
  },
  exercises: [
    {
      id: "p3-e1",
      title: "The loop from scratch",
      repo: "phase4-agents/01-react-from-scratch",
      effort: { fast: 30, integration: null, realistic: 50 },
      rung: "faded",
      proves: "implement",
      task: "Build a ReAct agent with two tools (a calculator and a web search) and a hard step cap + wall-clock timeout. Run it on a frontier model AND on qwen3.5:9b locally; document where local tool-calling wobbles and add validate-and-retry.",
      assesses: ["p3-o1", "p3-o5"],
      needs: ["p1-o1"],
      solution: [
        "Tools = a name→callable registry with JSON-schema validation on the arguments before you run anything.",
        "Local models flub argument formatting most — validate, repair-prompt once, then escalate or fail cleanly. That graceful ladder is the lesson.",
      ],
    },
    {
      id: "p3-e2",
      title: "Write three real tools",
      repo: "phase4-agents/02-tools",
      effort: { fast: 30, integration: null, realistic: 50 },
      rung: "faded",
      proves: "implement",
      task: "Implement three tools to spec — one read-only (fetch), one reversible write (draft), one that must be gated (delete). Give each a model-facing docstring, type hints, argument validation, and error-as-data returns. Then blank one docstring and watch the agent misuse it.",
      assesses: ["p3-o2"],
      solution: [
        "The gated tool refuses until the application has a human approval on file — approval is app state the model can't reach, never a tool argument it fills. An `approve: bool` parameter is a gate the model can open itself.",
        "The blank-docstring run is the point: the model literally cannot tell what the tool is for. Description IS the interface.",
      ],
    },
    {
      id: "p3-e3",
      title: "Add a human pause (HITL)",
      repo: "phase4-agents/03-hitl",
      effort: { fast: 40, integration: 25, realistic: 75 },
      rung: "faded",
      proves: "integrate",
      task: "Take your scratch agent and add an approval gate before the irreversible tool using LangGraph’s interrupt() + a checkpointer. Kill the process mid-pause and resume it by thread_id.",
      assesses: ["p3-o3"],
      solution: [
        "interrupt() suspends the graph and persists state; resuming replays from the checkpoint, not the start.",
        "Watching it survive a kill mid-pause is the aha — that durability is exactly why HITL needs a real framework.",
      ],
    },
    {
      id: "p3-e4",
      title: "Same agent, three frameworks",
      repo: "phase4-agents/04-framework-bakeoff",
      effort: { fast: 60, integration: 45, realistic: 150 },
      rung: "faded",
      proves: "integrate",
      task: "Run the SAME tool-using agent — look a fact up with a tool, then answer with it — through real LangGraph, Pydantic AI, and CrewAI, each returning the same result shape. Then score them on six dimensions (durability, recovery, complexity, observability, latency, cost) from measurements you recorded, and report which dimensions your test failed to separate.",
      assesses: ["p3-o4"],
      solution: [
        "The task has to be identical across all three. The tempting version gives each library the thing it is best at — LangGraph checkpointing, Pydantic AI validating, CrewAI orchestrating roles — and that is three demos, not a comparison; it concludes exactly what it assumed. Fix the task and the residue (glue lines, what survives the process, whether an offline test is even possible) belongs to the framework.",
        "Count tool calls, don't read the answer. A model that invents a plausible fact and skips the tool produces output indistinguishable from one that looked it up — `used_the_tool()` is the only honest check, and it is the same check in all three.",
        "Measure durability, don't quote it — and take the reading from somewhere else. Read `resumable` back out of `get_state` on a SECOND app built over the SAME checkpointer, not the one that just ran; an app holding its own `MemorySaver` remembers the call it just made whatever the framework is, so asking it measures object identity and prints it as durability. That one row is what decides whether you need a database.",
        "Read `undecided()` before the winners. Several dimensions will come back “not distinguished by this test”, and a 4% latency difference is noise — a matrix with a winner in every row is a matrix that guessed, and it is persuasive enough to outlive everyone's memory of how it was measured.",
        "Two traps cost an hour each. Pydantic AI's `TestModel` fills model-chosen arguments with throwaway strings, so pass the topic through `deps` and take `RunContext` in the tool; and leave `from __future__ import annotations` out of that module, because stringified annotations resolve against module globals where your function-local import isn't.",
        "CrewAI needs Python 3.12 and a model on the host. On 3.13+ it dies inside Chroma's Pydantic v1 shim with a message about `chroma_server_nofile` — a version bound wearing a library bug's clothes. That it constrains your interpreter and can't be tested offline at all is itself the observability row.",
      ],
    },
    {
      id: "p3-e5",
      title: "Blank editor: the loop and the leash, from nothing",
      rung: "independent",
      proves: "operate",
      task: "Empty directory, one file, no framework and no `before/` open anywhere. Write the reason–act–observe loop yourself: a hard step cap, a wall-clock deadline, two tools with real schemas, tool errors returned as observations rather than raised, and a final answer. Then deliberately break it — give it a goal it cannot achieve with the tools it has, and a tool that always errors — and prove it terminates. Because this one claims `operate`, the proof is a table of numbers, not a sentence: for each of the four runs (happy path, impossible goal, always-erroring tool, deadline shorter than one tool call) record steps taken against the cap, wall-clock elapsed against the budget, which limit stopped it, and what the final message said. A run that stopped because the model happened to give up is not the same result as a run your cap stopped, and only the step count tells you which you have. Ninety minutes.",
      assesses: ["p3-o1", "p3-o2", "p3-o5"],
      solution: [
        "The step cap is a `range()` or a counter you increment, not a sentence in the prompt. If you find yourself writing “remember, only 5 steps” you have rebuilt the thing the predict prompt on this page warned you about.",
        "The deadline is checked at the top of every iteration, not only after the model call. A single 90-second tool call should not be able to outlive a 60-second budget.",
        'A failing tool returns something like `{"error": "..."}` into the transcript and the loop keeps going. Raising kills the run and throws away the agent’s chance to try something else; errors are data, and the loop is where that principle earns its keep.',
        "The impossible goal terminates and reports failure rather than looping until the cap. An agent that hits `max_steps` on every hard task is technically contained and practically useless — you want it to notice, and the step count in your table is how you can tell the difference.",
        "The deadline row is the one people cannot fake. Set the budget to 5s with a tool that sleeps 10s and record the elapsed time: if it reads 10.2s, your deadline is checked in the wrong place and the cap is what saved you. Two containment mechanisms and only one of them working looks exactly like both working until the day the cap is high.",
        "Your tool schemas describe *when* to use each tool, not just its parameter types. The docstring is the interface the model reads; a schema with perfect types and no guidance produces an agent that calls the right function at the wrong moment.",
        "You wrote it without the framework. That is the whole point — everything in LangGraph and Pydantic AI is this loop with durability and types bolted on, and you can only evaluate what they add once you can produce what they wrap.",
      ],
    },
  ],
  workshop: {
    id: "w2",
    title: "Workshop · Your personal assistant agent",
    subtitle:
      "The capstone that ties Phase 4 together — and the agent you’ll keep upgrading for the rest of the course.",
    repo: "workshops/assistant",
    doc: "WORKSHOP-ASSISTANT.md",
    effort: { fast: 150, integration: 30, realistic: 300 },
    proves: "integrate",
    assesses: ["p3-o1", "p3-o2", "p3-o3", "p3-o5"],
    needs: ["p1-o1", "p2-o1"],
    blocks: [
      {
        kind: "p",
        text: "Build a real personal-assistant agent that does useful things across several services. This is the system you’ll teach to remember in Phase 5, harden in Phase 6, extend with your own MCP server in Phase 7, and deploy in Phase 8 — so build it clean. Everything is a **tool**; the agent is the loop from this phase with a proper toolbox and an approval gate on anything that sends or schedules.",
      },
      {
        kind: "callout",
        tone: "tip",
        title: "Local-first and free",
        text: "Use free/local tiers wherever possible: a local model for triage and summarization, real APIs (or their sandbox modes) for the connectors. The whole thing should run on your laptop with `docker compose up`. Keep credentials in env vars — never in code — because Phase 6 is going to attack this agent.",
      },
      {
        kind: "flow",
        title: "The assistant’s toolbox",
        nodes: [
          { label: "Read email", sub: "Gmail/IMAP — read-only" },
          { label: "Summarize inbox", sub: "local model" },
          { label: "Read news", sub: "fetch + parse a page" },
          { label: "Send Telegram", sub: "GATED: HITL" },
          { label: "Schedule event", sub: "GATED: HITL" },
        ],
      },
      {
        kind: "code",
        title: "The shape you’re filling in (before/tools.py)",
        code: `@tool
def read_emails(since: str = "today", limit: int = 20) -> list[dict]:
    """Read recent emails (read-only). Use to check or summarize the inbox."""
    ...   # TODO: connect to Gmail/IMAP, return [{from, subject, snippet}]

@tool(requires_approval=True)          # <- HITL: never fires without a human OK
def send_telegram(chat_id: str, message: str) -> str:
    """Send a Telegram message. IRREVERSIBLE — requires user approval."""
    ...

@tool(requires_approval=True)
def schedule_event(title: str, start_iso: str, duration_min: int) -> str:
    """Create a calendar event. Requires user approval before creating."""
    ...`,
      },
    ],
    deliverables: [
      {
        id: "w2-d1",
        text: "Agent can **read and summarize** recent email on request (read-only tool, no gate)",
        tier: "minimum",
      },
      {
        id: "w2-d2",
        text: "Agent can **fetch and summarize news** from a page you point it at",
        tier: "full",
      },
      {
        id: "w2-d3",
        text: "**Send Telegram** and **schedule an event** both work — and both **pause for human approval** before firing",
        tier: "minimum",
      },
      {
        id: "w2-d4",
        text: "Every external connection is a proper **tool**: docstring, type hints, validation, error-as-data",
        tier: "full",
      },
      {
        id: "w2-d5",
        text: "Hard step cap + timeout in code; runs on a **local model for triage/summarize**, escalating only when needed",
        tier: "full",
      },
      {
        id: "w2-d6",
        text: "All credentials come from **env vars**, never from code — Phase 8 is what turns this into a `docker compose up` stack, and Phase 6 is going to attack it",
        tier: "full",
      },
    ],
    stretch: [
      'Add a "morning brief" that chains inbox summary + top news into one message you approve, then sends.',
      "Log cost per run with the Phase-1 meter so you can see what the assistant costs per day.",
      "Add a second read-only connector of your own choosing — the toolbox pattern should feel routine before the next phase makes it remember things.",
    ],
  },
  checkpoint: [
    {
      id: "p3-q1",
      q: 'What actually makes something an "agent" rather than a chatbot?',
      a: "A loop with tools: the model can take an action, observe the result, and decide the next step — repeating until done. A chatbot is one prompt in, one answer out. The loop + tools + a stopping condition is the whole distinction.",
      demands: ["alternatives", "constraints"],
    },
    {
      id: "p3-q2",
      q: "Why is a tool’s docstring not just a comment?",
      a: "The model chooses and fills a tool using only its name, docstring, and type hints — nothing else. A vague docstring is a vague API. It should say both what the tool does and when to use it, written like a prompt.",
      demands: ["constraints", "failure-modes"],
    },
    {
      id: "p3-q3",
      q: "Why must iteration caps live in code, not the prompt?",
      a: "A prompt is a suggestion the model can ignore, especially under adversarial input or a rotted context. A hard loop bound, a wall-clock timeout, and a spend cap are guarantees — the difference between a contained failure and a runaway bill.",
      demands: ["alternatives", "failure-modes"],
    },
    {
      id: "p3-q4",
      q: "When would you pick Pydantic AI over LangGraph?",
      a: "When a single, well-typed agent with tools is all you need and a state graph would be overkill. LangGraph earns its ceremony when you need durability, branching, cycles, or HITL that pauses for a long time; Pydantic AI wins on minimal, type-safe simplicity. Say where that came from rather than reciting it: the bakeoff runs the **same** tool-using agent in both and scores six dimensions from measurements, and the row that actually decides it is durability — LangGraph leaves a checkpointed thread a second call can resume, Pydantic AI leaves nothing, and that is a measured `resumable` flag rather than a claim from a landing page. Note which rows came back a tie, too; a matrix that declares a winner on every dimension is one that laundered noise into a decision.",
      demands: ["alternatives", "constraints", "evidence"],
    },
    {
      id: "p3-q5",
      q: "What’s stronger than asking a human to approve a risky action — and why keep both?",
      a: "Least privilege: don’t give the agent the dangerous tool at all unless it truly needs it — an action it can’t take can’t be triggered by a bad instruction. Keep HITL too, as the backstop for the irreversible actions it genuinely must be able to perform.",
      demands: ["alternatives", "failure-modes"],
    },
  ],
  resources: [
    {
      label: "Anthropic — Building Effective Agents",
      url: "https://www.anthropic.com/research/building-effective-agents",
    },
    { label: "LangGraph docs", url: "https://langchain-ai.github.io/langgraph/" },
    { label: "Pydantic AI docs", url: "https://ai.pydantic.dev" },
    { label: "CrewAI docs", url: "https://docs.crewai.com" },
    { label: "ReAct paper (Yao et al.)", url: "https://arxiv.org/abs/2210.03629" },
    { label: "Ollama — tool calling", url: "https://ollama.com/blog/tool-support" },
  ],
};
