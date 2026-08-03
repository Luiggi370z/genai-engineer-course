# The GenAI Engineer Workbook

**An 18-week workbook that takes a working software engineer to shipping GenAI systems
they can defend — evaluated, guarded, deployed, and measured.**

You have two files:

- **`course.html`** — the workbook. One self-contained file: no server, no build, no
  network. Open it from disk. Your progress is saved in the browser's `localStorage`, so
  it lives in that one browser on that one machine. **Export**, **Import** and **Reset**
  at the bottom of the sidebar are how you move it or start over — export before you
  clear a cache or switch machines, because nothing else can recover it.
- **`genai-engineer-workbook-src.zip`** — the companion code. Every exercise ships as a
  `before/` scaffold with the judgement removed and an `after/` reference. This is the
  part you work in.

---

## Start here

```bash
# 1. Open the workbook and read Phase 1. Everything else follows from it.
open course.html

# 2. Unpack the companion code.
unzip genai-engineer-workbook-src.zip

# 3. Install the toolchain and pull the two models you need to begin.
#    Ollama goes on this machine, not in a container — it needs the GPU.
curl -LsSf https://astral.sh/uv/install.sh | sh
ollama pull qwen3.5:9b        # chat + tool calling
ollama pull nomic-embed-text  # embeddings

# 4. Do the first lesson. Its tests fail on purpose — turning them green is the work.
cd genai-engineer-workbook-src/src/phase1-foundations/01-universal-client/before
make setup && make test       # red: the TODOs are yours to fill in
$EDITOR src/client.py
make check                    # green: lint, types and tests
```

Two more models are worth pulling when you reach those phases rather than now:
`qwen3-coder:30b` for the Phase 3 judge (needs 32 GB of RAM — on a 16 GB machine use a
smaller or hosted judge), and `llama-guard3:8b` for the Phase 6 guardrails.

---

## What you need

**Software.** Python **3.11 through 3.14**, [uv](https://docs.astral.sh/uv/),
[Ollama](https://ollama.com) installed on your own machine, and Docker for the
Phase 8 deployment lessons. Install Ollama on the host rather than in a container:
Docker Desktop gives containers no GPU, and the difference on the course's own 9B
is 0.52 tokens per second against 81. Phase 8's stack runs its infrastructure in
compose and reaches your Ollama at `host.docker.internal:11434`.
That range is a range, not a floor: every lesson declares
`requires-python = ">=3.11,<3.15"` and CI runs the whole set at both ends on every
push, because an unbounded `3.11+` is a claim about versions that did not exist when
it was written. One lesson — 4.4, the framework bakeoff — pins **3.12** exactly,
because CrewAI's dependency tree does not build on anything newer. It declares that
itself and uv fetches the interpreter; you do not need 3.12 for anything else.

**Hardware.** Four honest tiers — pick yours and nothing you *learn* changes:

<!-- canonical:hardware -->
| Tier | What runs | What to know |
|------|-----------|--------------|
| Any machine | Every lesson's fast test suite (`make test`) | Offline, deterministic, no models, no keys — the whole course can be *completed* here |
| 16 GB | The course's working models locally: `qwen3.5:9b`, `gemma4:e4b`, embeddings, guard models | The recommended local path. The 30B eval judge does **not** fit here — swap in a smaller judge or a hosted one |
| 32–64 GB | + `qwen3-coder:30b` as a free local Phase 3 judge | The comfortable path; bigger judges are measurably better |
| No GPU / older laptop | Everything, against a hosted budget tier by changing one `base_url` | Needs an account, an API key, and network; costs real (small) money |
<!-- /canonical:hardware -->

Phase 1 carries the full sizing table. Both are generated from one canonical list, so
the short version here cannot quietly disagree with the long one in the workbook.

**Money.** The fast test tier of every lesson runs offline with zero API keys, so the
course can be completed spending nothing. Hosted providers — the no-GPU fallback and the
optional frontier comparisons — are metered and cost real (small) money.

**Skills.** No machine-learning background is needed and there is no maths derivation
anywhere in here. What is assumed, and what merely helps:

<!-- canonical:prerequisites -->
**Required — assumed on day one.**

- **Python (comfortable)** — type hints, async/await, Pydantic, uv or poetry, pytest
- **APIs & HTTP** — verbs, status codes, API-key auth, JSON, SSE/streaming, retry with backoff
- **Git/GitHub** — branching, PRs, code review
- **Docker basics** — Dockerfile, docker compose, multi-stage builds

**Helpful, not required** — each is either taught here or has a stated way around it.

- **A cloud** — any of AWS/GCP/Azure. Phase 8 deploys with compose on one box; a cloud makes the last mile familiar rather than possible
- **SQL** — joins and indexes make pgvector feel familiar, but every query the course writes is shown in full
- **Design patterns** — adapter/strategy and dependency injection carry this whole course; you can also just read them off the lessons that use them
- **Hardware** — any 16GB+ machine runs the local-model lessons; more RAM unlocks stronger models (sizing table in Phase 1). No GPU at all? Hosted budget tiers cover everything.
- **Light math** — vectors, cosine similarity, probability intuition. No PhD required, promise
<!-- /canonical:prerequisites -->

The workbook's opening screen carries the same two lists as a self-check.

**Scope.** This is a course about *building systems on top of models*. It deliberately
does not teach transformer mathematics or model architecture, pretraining and distributed
training, fine-tuning and alignment research, GPU kernels / quantization / serving at
scale, multimodal depth, or research methodology. None of that is needed for this job;
all of it is needed for a different one. The workbook's opening screen lists each with a
pointer to where to learn it, so you can tell on day one whether you are in the right
place.

---

## Where to get unstuck

1. **Re-read the failing test.** The `before/` tests describe the shape of the answer,
   not just that you are wrong.
2. **Check the phase's `VERIFIED.md`.** Each carries a dated stamp saying when its
   lessons last passed, and — where it recorded one — the exact version that run
   resolved to. Most record the date and the declared *ranges* rather than exact
   versions, because the lessons are version-bounded rather than locked: only the
   capstone ships a lockfile. GenAI dependencies break fast; if that date is old,
   expect drift, and upgrade one dependency at a time.
3. **Open `after/`.** It is a reference, not a cheat — read it, close it, then write
   your own.
4. **Run `genai-engineer-workbook-src/src/verify-lessons.sh`** if something looks broken
   in the code rather than in your work. It checks every lesson and names the unhappy one.

Full mechanics — the `make` targets, the library stack, version pinning, and the
lesson-by-lesson map — are in `genai-engineer-workbook-src/src/README.md`.

## License

MIT — use it, fork it, teach from it.
