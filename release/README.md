# The GenAI Engineer Workbook

**An 18-week workbook that takes a working software engineer to shipping GenAI systems
they can defend — evaluated, guarded, deployed, and measured.**

You have two files:

- **`course.html`** — the workbook. One self-contained file: no server, no build, no
  network. Open it from disk. Your progress is saved in the browser's `localStorage`,
  so it lives in that one browser on that one machine.
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
`qwen3-coder:30b` for the Phase 3 judge (needs ~32 GB of RAM — on a 16 GB machine use a
smaller or hosted judge), and `llama-guard3:8b` for the Phase 6 guardrails.

---

## What you need

**Software.** Python 3.11+, [uv](https://docs.astral.sh/uv/),
[Ollama](https://ollama.com), and Docker for the Phase 8 deployment lessons.

**Hardware.** Four honest tiers — pick yours and nothing you *learn* changes:

- **Any machine** runs every lesson's fast test suite offline: no models, no keys.
- **16 GB of RAM** runs the course's working models locally (`qwen3.5:9b`, embeddings,
  guard models). The 30B eval judge does not fit — use a smaller or hosted judge there.
- **32 GB of RAM** adds `qwen3-coder:30b` as a free local Phase 3 judge.
- **No GPU / older laptop:** every lesson runs against a hosted budget tier by changing
  one `base_url` — that needs an account, an API key, network, and small real money.

Phase 1 carries the full sizing table.

**Money.** The fast test tier of every lesson runs offline with zero API keys, so the
course can be completed spending nothing. Hosted providers — the no-GPU fallback and the
optional frontier comparisons — are metered and cost real (small) money.

**Skills.** You should already write Python comfortably (type hints, `async`/`await`,
Pydantic, pytest), know git, HTTP and JSON, and have met Docker. No machine-learning
background is needed and there is no maths derivation anywhere in here.

---

## Where to get unstuck

1. **Re-read the failing test.** The `before/` tests describe the shape of the answer,
   not just that you are wrong.
2. **Check the phase's `VERIFIED.md`.** Each carries a dated stamp saying when its
   lessons last passed and against which library versions. GenAI dependencies break
   fast; if that date is old, expect drift, and upgrade one dependency at a time.
3. **Open `after/`.** It is a reference, not a cheat — read it, close it, then write
   your own.
4. **Run `genai-engineer-workbook-src/src/verify-lessons.sh`** if something looks broken
   in the code rather than in your work. It checks every lesson and names the unhappy one.

Full mechanics — the `make` targets, the library stack, version pinning, and the
lesson-by-lesson map — are in `genai-engineer-workbook-src/src/README.md`.

## License

MIT — use it, fork it, teach from it.
