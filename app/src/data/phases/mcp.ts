// Generated from the shipped course bundle by scripts/extract-data.mjs.
// Edit freely from here on — this file is the source of truth for the content.

import type { PhaseContent } from "../types";

export const mcp: PhaseContent = {
  id: "p5",
  weeks: "Weeks 14–15",
  color: "#0891B2",
  title: "MCP: The Universal Tool Port",
  tagline:
    "One protocol so any agent can use any tool. Consume existing servers, build your own over a REST API, get the auth right — then plug it into the assistant you built.",
  tldr: "MCP is tool-calling with a wire protocol, so any agent can use any tool. You consume an existing server through the five-beat handshake on the stateless 2026 spec, build your own over a REST API with tools, resources and prompts, and pick the auth each deployment needs.",
  objectives: [
    {
      id: "p5-o1",
      text: "**Explain** what MCP is, the problem it solves, and how it sits on top of the tool-calling from Phase 4",
    },
    {
      id: "p5-o2",
      text: "**Consume** an existing MCP server from a client — the five beats, on the stateless 2026 protocol",
    },
    {
      id: "p5-o3",
      text: "**Build** your own MCP server over a REST API — tools, resources and prompts — with `MCPServer` (SDK v2)",
    },
    {
      id: "p5-o4",
      text: "**Choose** the right authentication per deployment — none (stdio), Bearer/API key, or OAuth 2.1 + PKCE — and defend the choice",
    },
  ],
  recall: [
    {
      id: "p5-r1",
      q: "What makes a tool definition good enough for a model to use correctly? Name the parts before you read on.",
      a: "A typed schema for the arguments, a docstring that says *when* to reach for this tool and not merely what it does, validation that rejects bad input before it reaches the outside world, and errors returned as data so a failure becomes an observation the agent can react to. The docstring is the interface. That matters doubly here, because an MCP server publishes those descriptions to clients you will never meet — a vague one is now everyone’s problem.",
      from: "p3-o2",
    },
    {
      id: "p5-r2",
      q: "Cold: what is a “tool” in the Phase 4 sense, and why is a retrieval call one?",
      a: "Anything that touches the world outside the model’s context — a database read, an HTTP request, a file write, a search over your corpus. Retrieval is a tool call like any other, which is why the same schema-plus-validation discipline applies. MCP does not replace this idea; it standardises how the definitions travel between processes.",
      from: "p3-o1",
    },
    {
      id: "p5-r3",
      q: "Untrusted text arrives from a tool your agent just called. Which attack family is that, and what stops it?",
      a: "Indirect prompt injection — instructions hidden in retrieved content, a fetched web page, an email body, or a tool’s output. The defenses are layered and the last one is containment rather than filtering: least-privilege tools, no unreviewed outbound actions, an egress allowlist. Keep it in mind for the next 45 minutes, because a third-party MCP server is precisely a tool output you do not control, arriving from code you did not write.",
      from: "p4-o3",
    },
  ],
  concepts: [
    {
      id: "p5-c1",
      title: "The problem MCP solves",
      tag: "fundamentals",
      teaches: ["p5-o1"],
      blocks: [
        {
          kind: "predict",
          prompt:
            "Your company has **4 agents** — a support bot, an internal assistant, a code reviewer, a data analyst — and **6 systems** they each need to reach: Jira, Postgres, the invoice API, Slack, the wiki, and GitHub. Writing hand-rolled tools the Phase 4 way, how many separate integrations does someone have to write and maintain? Now: what is that number if all six speak one protocol? Work both out before reading on.",
          answer:
            "**24 without, 10 with.** Every agent needs its own client code for every system, so 4 × 6 = 24 integrations, each with its own schema drift and its own bugs. With one protocol you write 6 servers and 4 clients: 10 pieces, and the next agent costs 1 rather than 6. That is not a small constant-factor win, it is the difference between multiplication and addition.",
          consolidation:
            "This is the entire argument for MCP, and it is worth having derived it yourself rather than being told it — because the same arithmetic tells you when *not* to bother. One agent and one system is 1 integration either way, and the protocol is pure overhead. The payoff arrives with the second consumer, which is also the moment the second question starts to matter: those 6 servers are now reachable by clients you do not control, so their descriptions, their validation, and their auth are no longer private implementation details.",
        },
        {
          kind: "p",
          text: "In Phase 4 you learned that every connection to the outside world is a **tool** — but a tool you write by hand works only in *your* agent, and everyone else rewrites the same invoice lookup for theirs. Before USB-C, every device had its own charger. **MCP (Model Context Protocol)** is USB-C for agent tools: write one server for your invoice system, and Claude, ChatGPT, Cursor and your own agents can all call it, unchanged.",
        },
        {
          kind: "list",
          items: [
            "It’s a real, governed standard: under the Linux Foundation’s Agentic AI Foundation since late 2025, backed by Anthropic, OpenAI, Google, and Microsoft, with ~10,000 public servers (as of mid-2026).",
            "Mental model: MCP sits **on top of** the tool calling from Phase 4. It doesn’t replace your REST API — it wraps capabilities so any client can **discover** them at runtime, over a **standard transport**, in a **session**.",
            "The payoff for you: your Phase-4 assistant can pick up a brand-new server with **zero code changes**, because the capability list is data the client fetches, not code you hard-wire.",
          ],
        },
        {
          kind: "callout",
          tone: "tip",
          title: "Why MCP gets its own phase",
          text: "MCP is now table stakes in 2026 GenAI interviews and real jobs — and it has enough moving parts (three primitives, two transports, a session lifecycle, and a genuinely tricky auth story) that cramming it into the agents phase shortchanged it. Here it gets the room it deserves.",
        },
      ],
    },
    {
      id: "p5-c2",
      title: "Host, client, server, and the five-beat handshake",
      tag: "how it works",
      teaches: ["p5-o1", "p5-o2"],
      blocks: [
        {
          kind: "p",
          text: "The naming trips everyone up, so pin it. The **host** is the app the user touches — Claude Desktop, Cursor, or your own agent. Inside the host runs one **client** per connection, and each client talks to exactly one **server** — your code, exposing capabilities. One host can hold many clients, each wired to a different server. The moment your Phase-4 assistant opens an MCP client, it *is* a host.",
        },
        {
          kind: "flow",
          title: "Every client session, same five beats",
          nodes: [
            { label: "Connect", sub: "open the transport" },
            { label: "initialize", sub: "capability handshake" },
            { label: "list_tools / resources", sub: "runtime discovery" },
            { label: "call_tool / read_resource", sub: "actually use it" },
            { label: "Close", sub: "tear down" },
          ],
        },
        {
          kind: "p",
          text: "On the wire it’s just **JSON-RPC 2.0** — plain request/response messages. You almost never touch that layer (the SDK does), but knowing it’s there explains the two transports you choose between:",
        },
        {
          kind: "list",
          items: [
            "**stdio** — the client launches your server as a child process and talks over its stdin/stdout. No network, nothing to deploy, no auth needed (OS user isolation). Where you start, and what desktop apps use.",
            "**Streamable HTTP** — your server is a web service at a URL; remote clients connect over HTTP. This is how you share a server with a team — and where authentication becomes mandatory.",
            "**In-memory** — v2 lets a client take the server *object* directly, with no transport at all. That is how you test: real protocol messages, no network, no subprocess.",
          ],
        },
        {
          kind: "callout",
          tone: "fix",
          title: "2026: the beats stayed, the session went away",
          text: "The 2026-07-28 spec moved MCP from a **stateful, bidirectional** protocol to **stateless request/response**. In the old world a client opened a long-lived session and held it open. Now that is a compatibility path only. The five beats still describe exactly what a client *does* — they simply no longer have to happen inside one held-open connection. Practical upshot: never assume the server remembers you between calls.",
        },
        {
          kind: "code",
          title: "Consuming a server — the five beats in code",
          code: `from mcp import Client            # v2: one client for every transport

# Client takes an in-memory server object, a URL, or a transport --
# the SAME code works for all three. That is the protocol doing its job.
async with Client("http://localhost:8000/mcp") as client:   # 1. connect
                                                            # 2. initialize (automatic)
    tools = await client.list_tools()                       # 3. discover
    out = await client.call_tool("lookup_invoice",          # 4. call
                                 {"invoice_id": "INV-88231"})
    print(out.content[0].text, out.is_error)   # v2 fields are snake_case
                                                            # 5. close (context exit)

# In tests, skip the network entirely -- pass the server object itself:
#     async with Client(build_server()) as client: ...`,
        },
        {
          kind: "callout",
          tone: "tip",
          title: "Discovery is the whole point",
          text: 'With a REST API the caller must already know every endpoint. With MCP the client asks the server at runtime "what can you do?" and gets back tool names, descriptions, and JSON schemas. That’s why one agent can adopt a new server with no code change — capabilities are data, not code.',
        },
      ],
    },
    {
      id: "p5-c3",
      title: "Building a server: three primitives, one decorator each",
      tag: "MCPServer · SDK v2",
      teaches: ["p5-o3"],
      blocks: [
        {
          kind: "p",
          text: 'You will basically never write JSON-RPC by hand. **`MCPServer`** turns a normal Python function into an MCP primitive with a decorator and generates the JSON Schema from your type hints — the exact same "docstring is the interface" skill from Phase 4, now exposed to the whole ecosystem.',
        },
        {
          kind: "callout",
          tone: "warn",
          title: "Two different projects are called FastMCP — know which one a tutorial means",
          text: "**FastMCP 1.0** was contributed into the official `mcp` package in 2024. SDK **v2 (2026-07-28) renamed that class to `MCPServer`** and *removed* the old `mcp.server.fastmcp` path — removed, not deprecated, so v1 code fails on import. Separately, **standalone FastMCP** (Jeremiah Lowin, now PrefectHQ) is a different project that reached **3.0 GA in February 2026** and has its own roadmap (`pip install fastmcp`). Same name, two projects, actively diverging. This course uses the **official SDK**.",
        },
        {
          kind: "code",
          title: "A server with all three primitives",
          code: `from mcp.server import MCPServer      # v2 (v1's FastMCP path was removed)

mcp = MCPServer("invoices")

@mcp.tool()
def lookup_invoice(invoice_id: str) -> dict:
    """Fetch an invoice by ID. Use when the user asks about a specific invoice."""
    return api.get(f"/invoices/{invoice_id}")   # wraps your existing REST endpoint

@mcp.resource("invoices://recent")
def recent() -> str:
    """Read-only: the 10 most recent invoices, for context."""
    return format(api.get("/invoices?limit=10"))

@mcp.prompt()
def dispute(invoice_id: str) -> str:
    """A reusable template for drafting a dispute about an invoice."""
    return f"Draft a polite dispute for invoice {invoice_id}. Be specific."

if __name__ == "__main__":
    mcp.run()                      # stdio; or transport="streamable-http"

# You never write JSON Schema -- the SDK derives it from your type hints, and the
# docstring becomes the description the model reads when choosing a tool.`,
        },
        {
          kind: "list",
          items: [
            "**@mcp.tool()** — an action (like POST). Name + docstring + type hints = the schema the model sees. Write the docstring like a prompt.",
            '**@mcp.resource("scheme://path")** — read-only data (like GET) the client pulls into context on demand.',
            "**@mcp.prompt()** — a reusable prompt template the host can offer the user by name.",
          ],
        },
        {
          kind: "callout",
          tone: "tip",
          title: "Inspector before agent, always",
          text: 'Run `npx @modelcontextprotocol/inspector uv run python -m src.server` — a browser UI that lists your tools and lets you call them by hand. Get it green there BEFORE any agent connects. That cleanly separates "my server is broken" from "my agent is broken," and it will save you hours.',
        },
      ],
    },
    {
      id: "p5-c4",
      title: "Authentication: pick the right door",
      tag: "the tricky part",
      teaches: ["p5-o4"],
      blocks: [
        {
          kind: "p",
          text: "Auth is where most MCP projects stumble, and it’s a favorite interview probe. The rule is simple: **the right method depends on the transport and the trust boundary.** Applying one method everywhere is the pattern teams regret.",
        },
        {
          kind: "table",
          headers: ["Method", "Use when", "Watch out for"],
          rows: [
            [
              "None (env vars)",
              "Local stdio server — only your OS user can reach it; upstream secrets come from the environment.",
              "Never hard-code keys; pull from env. This is correct, not lazy, for local.",
            ],
            [
              "Bearer token / API key",
              "Internal or team remote server behind a gateway; every client is a known app.",
              "Plaintext-in-config leaks; use ${env:VAR} references, HTTPS only, never in query strings.",
            ],
            [
              "OAuth 2.1 + PKCE",
              "Any public-facing remote server, or one acting on behalf of users who must consent.",
              "Mandatory per the Nov-2025 spec for public servers. Validate token audience; never pass tokens through.",
            ],
          ],
        },
        {
          kind: "list",
          items: [
            "**OAuth 2.1 separates the token issuer from your server.** Your MCP server is a *resource server*: it accepts a short-lived, scoped Bearer token, validates signature + expiry + **audience**, then serves the request. Auth stays out of the protocol itself.",
            "**PKCE (S256) is non-negotiable** for public servers — the spec bans the implicit grant and plain PKCE. All endpoints HTTPS; Bearer tokens never in URLs.",
            "**The confused-deputy trap:** never forward a client’s token to an upstream API. If your server needs to call GitHub on the user’s behalf, it obtains its *own* separate token. Token passthrough is explicitly forbidden.",
            "**The 2026 reality check:** an audit found ~25% of public MCP servers had *no* auth and ~53% relied on long-lived static keys. Getting this right is a real differentiator.",
          ],
        },
        {
          kind: "callout",
          tone: "warn",
          title: "Tool poisoning is an MCP-specific attack",
          text: 'Remember the Phase-6 attack catalog: because a client reads tool **descriptions** at discovery, a malicious server can hide instructions in a tool’s name or description, and a compromised tool can return adversarial content as "trusted" tool output. Vet the servers you connect to, treat tool output as untrusted, and allow-list tools — auth protects your server; skepticism protects your client.',
        },
      ],
    },
  ],
  example: {
    title: "Field story: one server, every assistant",
    text: "A fintech team wrapped their internal invoicing API in a single MCP server — three tools, a recent-invoices resource, OAuth 2.1 for the remote deployment. Within a month it was being used unchanged by their support agents, an internal Cursor workflow for the finance team, and a customer-facing Claude integration. They wrote the tools once; three different hosts discovered and used them with zero coordination. That is the entire promise of a standard, delivered.",
  },
  exercises: [
    {
      id: "p5-e1",
      title: "Be a client first",
      repo: "phase7-mcp/01-consume-a-server",
      rung: "faded",
      task: "Before building anything, connect a Python ClientSession to a prebuilt reference server over stdio. Run the handshake, list its tools and resources, call one. (Needs Node/npx on PATH.)",
      assesses: ["p5-o2"],
      needs: ["p3-o2"],
      solution: [
        "The lifecycle never changes: connect → initialize → list → call → close. Internalize that order.",
        "Using a server you didn’t write means zero server code to debug — anything that breaks is your client. That’s why we go consumer-first.",
      ],
    },
    {
      id: "p5-e2",
      title: "Wrap a REST API as an MCP server",
      repo: "phase7-mcp/02-rest-to-mcp",
      rung: "faded",
      task: "Take a small public REST API (weather, or the provided toy service) and expose it as an MCP server with 3 tools, one resource, and one prompt. Verify everything in the MCP Inspector — no agent yet.",
      assesses: ["p5-o3"],
      needs: ["p3-o2"],
      solution: [
        "One tool per meaningful endpoint; docstrings written for the model; validate arguments before calling the API.",
        "Green in the Inspector = your protocol layer is correct. That’s the entire goal of this rung.",
      ],
    },
    {
      id: "p5-e3",
      title: "Three doors: stdio, Bearer, OAuth",
      repo: "phase7-mcp/03-auth-modes",
      rung: "faded",
      task: "Deploy your server three ways: as a local stdio server (env-var secrets), as a remote HTTP server behind a static Bearer token, and as a remote server with OAuth 2.1 + PKCE. Write down which you’d use for a personal tool, a team tool, and a public SaaS integration.",
      assesses: ["p5-o4"],
      solution: [
        "stdio → personal; Bearer → internal/team; OAuth 2.1 → public or on-behalf-of-user. Match method to trust boundary.",
        "Validate token audience on the OAuth path, and confirm you never forward the client token upstream (obtain your own).",
      ],
    },
    {
      id: "p5-e4",
      title: "Blank editor: a server for something you actually use",
      rung: "independent",
      task: "Empty directory, no template, no copying from exercise 2. Pick a service you personally use that has an API — your note app, a home-automation hub, your bank’s export endpoint, a hobby project — and expose it over MCP from scratch: two tools, one resource, one prompt. Then prove it in the Inspector, and finally connect a client you also write yourself and call one tool end to end. The unfamiliar API is the point: this is the first time nobody has picked a well-behaved one for you.",
      assesses: ["p5-o2", "p5-o3"],
      needs: ["p3-o2"],
      solution: [
        "You wrote the server before the client and verified it in the Inspector first. Debugging two unproven halves at once is the trap, and the consumer-first ordering in exercise 1 existed to teach you exactly this instinct.",
        "Your tool docstrings would let a model that has never seen your service choose correctly between your two tools. Read them back as if you were the model: if both descriptions could apply to the same request, the schema is fine and the interface is broken.",
        "Arguments are validated in your server before the upstream call, and upstream failures come back as structured errors rather than tracebacks. A 500 from your bank should reach the agent as something it can react to.",
        "You picked the auth mode deliberately and can say what trust boundary it matches — and no secret ended up in the tool arguments or the resource body, where a client you do not control would see it.",
        "The resource and the prompt are not filler. If you cannot say why that data is a resource rather than a tool call, you have three tools and a habit of following templates.",
        "It works against an API that was not designed for this course. Real endpoints paginate oddly, return inconsistent nulls, and rate-limit you — and handling that unassisted is the difference between having followed exercise 2 and being able to do the job.",
      ],
    },
  ],
  workshop: {
    id: "w4",
    title: "Workshop · Your own MCP, used by your assistant",
    subtitle:
      "Build an MCP server for a service you care about — then let your Phase-4 assistant consume it as a tool.",
    repo: "workshops/assistant",
    assesses: ["p5-o2", "p5-o3", "p5-o4"],
    needs: ["p3-o2"],
    blocks: [
      {
        kind: "p",
        text: "The payoff workshop: build a real MCP server exposing a service of your choice — your notes, a habit tracker, a home API, anything with a few operations — verify it in the Inspector, secure it appropriately, then wire it into your Workshop-4 assistant so it discovers and calls the server like any other tool.",
      },
      {
        kind: "p",
        text: "This is the moment the whole course clicks: the assistant from Phase 4, taught to remember in Phase 5 and hardened in Phase 6, gains new powers through a standard protocol with zero changes to its core loop.",
      },
      {
        kind: "callout",
        tone: "tip",
        title: 'The "zero code change" test',
        text: "The win condition isn’t just that your server works — it’s that your assistant picks up its tools by **discovery**, without you hand-coding each one into the agent. Add a new tool to the server, restart, and the assistant can use it immediately. That’s the standard doing its job.",
      },
      {
        kind: "flow",
        title: "What connects to what",
        nodes: [
          { label: "Your service", sub: "notes / tracker / API" },
          { label: "Your MCP server", sub: "MCPServer: tools + resource + prompt" },
          { label: "Auth", sub: "stdio local, or Bearer/OAuth remote" },
          { label: "Assistant (Workshop 4)", sub: "opens a client, discovers tools" },
          { label: "It just works", sub: "discovered, not hard-coded" },
        ],
      },
      {
        kind: "code",
        title: "The assistant gains your server (before/wire_mcp.py)",
        code: `# In your Workshop-4 assistant -- add an MCP client, don't hand-code tools
from mcp import Client

async def load_mcp_tools(target):
    async with Client(target) as client:
        discovered = await client.list_tools()       # <- discovery, not hard-coding
        return [as_agent_tool(t) for t in discovered.tools]   # TODO: adapt

# Now the assistant can call your notes/tracker/home tools alongside email, news,
# telegram and calendar -- all through one uniform interface. Add a tool to the
# server, restart, and the assistant can use it with NO assistant code change.`,
      },
    ],
    deliverables: [
      {
        id: "w4-d1",
        text: "An MCP server exposing at least **3 tools, 1 resource, and 1 prompt** over a real service",
      },
      { id: "w4-d2", text: "Verified in the **MCP Inspector** before any agent connects" },
      {
        id: "w4-d3",
        text: "Secured correctly for its deployment: **env-var secrets (stdio)** or **Bearer/OAuth (remote)** with audience validation",
      },
      {
        id: "w4-d4",
        text: "Your **Workshop-4 assistant consumes it via discovery** — tools are listed at runtime, not hard-coded",
      },
      {
        id: "w4-d5",
        text: "Adding a new tool to the server makes it usable by the assistant **with no assistant code change**",
      },
    ],
    stretch: [
      "Deploy the server remotely with OAuth 2.1 + PKCE and connect the assistant over Streamable HTTP.",
      "Add tool-poisoning defenses on the client side: allow-list which discovered tools the assistant may actually call.",
      "Publish the server’s config so a teammate can connect their own client to it.",
    ],
  },
  checkpoint: [
    {
      id: "p5-q1",
      q: "What does MCP add on top of plain tool calling?",
      a: "Runtime discovery of tools/resources/prompts, a standard transport (stateless request/response since the 2026 spec), and write-once-use-everywhere interop. Tool calling is how one agent invokes one function; MCP is how any client discovers and uses any server’s capabilities.",
    },
    {
      id: "p5-q2",
      q: "Walk the five beats of a client session.",
      a: "Connect (open the transport) → initialize (capability handshake) → list_tools/list_resources (runtime discovery) → call_tool/read_resource (use it) → close (tear down). Every client you ever write repeats exactly this.",
    },
    {
      id: "p5-q3",
      q: "Which auth method for a local tool, a team tool, and a public SaaS server — and one trap for each?",
      a: "Local stdio → none, env-var secrets (trap: hard-coding keys). Team remote → Bearer/API key over HTTPS (trap: plaintext in config). Public → OAuth 2.1 + PKCE (trap: forwarding the client token upstream — the confused-deputy vulnerability; get your own token).",
    },
    {
      id: "p5-q4",
      q: "Why verify a server in the Inspector before connecting an agent?",
      a: "It isolates protocol bugs from agent bugs. If the Inspector can list and call your tools, your server is correct — so anything that breaks after wiring the agent is the agent’s fault, not the protocol’s.",
    },
  ],
  resources: [
    { label: "MCP — spec & SDKs", url: "https://modelcontextprotocol.io" },
    {
      label: "MCP — official Python SDK",
      url: "https://github.com/modelcontextprotocol/python-sdk",
    },
    { label: "MCP Inspector", url: "https://github.com/modelcontextprotocol/inspector" },
    {
      label: "MCP authorization spec (OAuth 2.1)",
      url: "https://modelcontextprotocol.io/specification/draft/basic/authorization",
    },
    {
      label: "Standalone FastMCP 3.x (a different project)",
      url: "https://gofastmcp.com",
    },
    {
      label: "Simon Willison — MCP security problems",
      url: "https://simonwillison.net/2025/Apr/9/mcp-prompt-injection/",
    },
  ],
};
