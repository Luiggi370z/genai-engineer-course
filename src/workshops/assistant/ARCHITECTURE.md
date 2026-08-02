# Architecture — the composed assistant

Two diagrams: what the pieces are (and which tier each one swaps at), and what one
request actually goes through (and where the trust boundaries sit). Decisions with
alternatives and consequences live in [`adr/`](adr/); threats in
[`THREAT-MODEL.md`](THREAT-MODEL.md); incidents in [`RUNBOOK.md`](RUNBOOK.md).

## Components and tiers

Every port has two adapters: an offline one (default — zero keys, deterministic,
what the fast tests drive) and a real one (one env var each — what the composed
stack runs). The service code cannot tell which is plugged in; that indifference
is enforced by the tests, not just claimed.

```mermaid
flowchart LR
    subgraph edge["HTTP edge (api.py)"]
        MW["rate limit + concurrency cap<br/>(resilience.py)"]
        AUTH["JWT gate — optional<br/>(auth.py)"]
        EP["/health /ingest /ask<br/>/ask/stream /approve"]
    end

    subgraph core["pipeline (core.py) — wired by the composition root (service.py)"]
        GR["guardrails.py<br/>screen · spotlight · output_ok"]
        AG["agent.py<br/>loop · HITL pause"]
        OBS["observe.py<br/>span per run + per tool"]
    end

    subgraph ports["ports → offline | real adapter"]
        RAG["rag<br/>InMemoryRag BM25 | Qdrant"]
        MEM["memory<br/>in-process | SQLite"]
        BRAIN["composer<br/>offline stitcher | Ollama"]
        TOOLS["tools<br/>stubs | Telegram/RSS + MCP"]
        SPANS["spans<br/>in-memory | + OTLP collector"]
    end

    subgraph state["one SQLite file"]
        AUD["audit_log.py"]
        IDEM["idempotency.py"]
        SMEM["sqlite_memory.py"]
    end

    MW --> AUTH --> EP --> GR --> AG
    AG --- OBS
    AG --> RAG & MEM & BRAIN & TOOLS
    OBS --> SPANS
    EP --> AUD
    EP --> IDEM
    MEM --- SMEM
```

## One request, end to end

The trust rule that shapes the whole flow: **content is never trusted because of
where it was stored, only because of where it came from** — so user input,
retrieved documents and tool output are each screened at their own boundary, and
approval is trusted state (`/approve` grants), never text.

```mermaid
sequenceDiagram
    participant U as caller
    participant S as api.py → core.py
    participant G as guardrails
    participant A as agent loop
    participant R as rag (tenant-scoped)
    participant T as tools (hardened)
    participant L as audit log

    U->>S: POST /ask (+ Bearer JWT when auth is on)
    S->>S: rate limit · concurrency cap · resolve subject
    S->>G: screen(question)
    alt injection
        G-->>S: blocked
        S->>L: policy.blocked
        S-->>U: refusal
    else clean
        S->>R: search(question, tenant=subject)
        R-->>S: docs
        S->>G: screen each doc (drop poisoned, redact PII)
        S->>A: run under a traced span, approvals = grants
        A->>T: tool call (gated → pause unless a grant is live)
        T->>G: screen tool output before it becomes evidence
        A-->>S: evidence + audit trail
        S->>L: tool.ran / tool.pending
        S->>S: compose (offline stitcher | Ollama, evidence spotlighted)
        S->>G: output_ok(answer)
        S-->>U: answer + citations [{id, source, snippet}]
    end
```

The same pipeline serves `/ask/stream` as SSE — the output gate runs on the
accumulated text and the `done` event carries the verdict. A replayed `/approve`
is deduplicated by `Idempotency-Key`, and each grant is consumed by the run that
uses it, so "approved once" means "fires once".
