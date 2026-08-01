// Generated from the shipped course bundle by scripts/extract-data.mjs.
// Edit freely from here on — this file is the source of truth for the content.

import type { PhaseContent } from "../types";

export const retrieval: PhaseContent = {
  id: "p2",
  weeks: "Weeks 3–4",
  color: "#2563EB",
  title: "Retrieval That Actually Works",
  tagline:
    "Toy RAG demos take an afternoon. Here you build retrieval you can defend with numbers — and debug under interview pressure.",
  tldr: "Hybrid search plus a reranker, chunking chosen from evidence rather than blog folklore, and an offline gate of sliced golden questions that makes every retrieval change measurable. Ends with the stage-by-stage debugging drill interviewers actually hand you.",
  objectives: [
    {
      id: "p2-o1",
      text: "**Combine** keyword + vector search with a reranker, and justify why each piece earns its keep",
    },
    { id: "p2-o2", text: "**Choose** chunking by evidence, not blog folklore" },
    {
      id: "p2-o3",
      text: "**Build** a fast, offline gate — sliced golden questions plus lexical metrics — so every retrieval change is measurable before Phase 3 makes it judged",
    },
    {
      id: "p2-o4",
      text: "**Diagnose** a broken RAG system stage by stage — the thing interviewers actually hand you",
    },
  ],
  recall: [
    {
      id: "p2-r1",
      q: "Your retriever misses every query that contains an invoice number like `INV-88231`, even though the document is definitely in the index. Using only what Phase 1 taught you about embeddings, why?",
      a: "Embeddings encode *meaning*, and an opaque ID has none — the tokenizer shreds `INV-88231` into sub-token fragments that sit nowhere useful in vector space, so cosine similarity has nothing to latch onto. This is the exact miss you were told to remember at the end of the embed-and-index exercise, and it is the entire argument for the hybrid search you are about to build.",
      from: "p1-o3",
    },
    {
      id: "p2-r2",
      q: "Without looking: which field on an API response tells you what a call actually cost, and why is estimating from character count not good enough?",
      a: "The `usage` object — input, output, cached and reasoning tokens. Estimating is wrong in both directions: tokenizers differ per vendor by 15–20% on the same text, cached tokens bill at a fraction of list price, and thinking models bill reasoning tokens you never see in the output. You will need this in a moment, because a reranker changes your cost profile and you cannot claim it is worth it without the real number.",
      from: "p1-o2",
    },
    {
      id: "p2-r3",
      q: "You are told to swap your vector store from numpy to Qdrant. How much of a well-built Phase 1 pipeline has to change, and what does that tell you about where the real design decisions were?",
      a: "Two functions: index and search. Everything else — chunking, embedding, the retrieval contract — is untouched, because the store was always behind an interface. The decisions that mattered were chunking and what you embed; the database was an implementation detail. Hold onto that, because this phase is going to spend all its effort on the parts that actually move recall.",
      from: "p1-o3",
    },
  ],
  concepts: [
    {
      id: "p2-c1",
      title: "Why Ctrl+F still matters",
      tag: "core",
      teaches: ["p2-o1"],
      blocks: [
        {
          kind: "p",
          text: "Embeddings are a brilliant librarian who understands what you **mean** — and completely whiffs on “invoice INV-88231” because IDs get shredded into meaningless sub-tokens. Old-school keyword search (BM25) is Ctrl+F with a ranking brain: dumb about meaning, deadly on exact strings. **Use both, fuse the rankings (RRF), and you cover each other’s blind spots.** Qdrant, Weaviate and Milvus do this natively.",
        },
        {
          kind: "flow",
          title: "Cast a wide net, then get picky",
          nodes: [
            { label: "Question" },
            { label: "Hybrid fetch", sub: "keywords + vectors, top 20–150" },
            { label: "Reranker", sub: "reads each pair properly" },
            { label: "Best 3–5 survive" },
            { label: "Generate" },
          ],
        },
        {
          kind: "p",
          text: "The **reranker** is a second interviewer: slower, but it actually reads the candidate with the question instead of comparing résumé keywords. Cohere Rerank and Voyage are hosted picks; **BGE-reranker-v2 runs free on your laptop** and pairs perfectly with an all-local stack.",
        },
        {
          kind: "code",
          title: "Fuse keyword + vector ranks (RRF)",
          code: `# You do NOT write this. Qdrant fuses both arms server-side:
hits = client.query_points("docs",
    prefetch=[models.Prefetch(query=dense_q,  using="dense", limit=20),
              models.Prefetch(query=sparse_q, using="kw",    limit=20)],
    query=models.FusionQuery(fusion=models.Fusion.RRF),
    limit=5).points

# What RRF is doing under the hood, for your own understanding:
#   score(doc) = sum over each ranked list of  1 / (k + rank)      (k is ~60)
# Rank-based, so it needs no score calibration between the two arms -- which is
# exactly why it beats trying to average a BM25 score with a cosine score.`,
        },
      ],
    },
    {
      id: "p2-c2",
      title: "Upgrades ranked by payoff",
      teaches: ["p2-o1", "p2-o2"],
      blocks: [
        {
          kind: "predict",
          prompt:
            "Your Phase 1 pipeline retrieves the right chunk 61% of the time and you have one afternoon. Rank these four by how much recall each buys: **(a)** upgrade to the best embedding model money can buy, **(b)** add BM25 alongside vectors and fuse the rankings, **(c)** prepend one model-written sentence of context to each chunk before embedding, **(d)** halve your chunk size. Write your ranking down before reading the list below.",
          answer:
            "Roughly **c, b, d, a**. Contextual retrieval — that one prepended sentence — cut retrieval failures by about 49% in Anthropic’s measurements, and by 67% combined with reranking. Hybrid fusion is next and nearly free. Chunk size matters but is corpus-specific, which is why it is a measurement and not a rule. The shiny embedding model is last: swapping a good embedder for a slightly better one is usually a couple of points.",
          consolidation:
            "Most people rank (a) first, because it is the change that feels like an upgrade — a bigger model, a better number on a leaderboard. The three that beat it all work by *changing what you put in the index* rather than by changing the machine that reads it. That is the shape of nearly every retrieval win, and it is why this phase’s objective 3 is to build the offline gate first: the ranking above came from someone else’s corpus, and the only version of it that should govern your system is the one you measured on yours.",
        },
        {
          kind: "list",
          items: [
            "**Contextual retrieval — big payoff.** Before embedding each chunk, have a cheap model prepend one sentence of “where this came from.” Anthropic measured retrieval failures dropping ~49% (67% with reranking). It’s a parallel batch job — run it free on a local model overnight.",
            "**Small-to-big — big payoff, tiny effort.** Search over small chunks, but hand the model the larger parent section. Precision finds it; context explains it.",
            "**Query rewriting / multi-query — decent.** Let a model rephrase the question a few ways and merge results.",
            "**HyDE — situational.** Embed a **hypothetical answer** instead of the question. Shines on jargon-heavy corpora, costs latency.",
            "**GraphRAG — only when asked.** Knowledge graphs answer “themes across everything” questions; for ordinary doc Q&A they’re an expensive detour.",
          ],
        },
        {
          kind: "code",
          title: "Contextual retrieval: one cheap sentence, big payoff",
          code: `def contextualize(doc: str, chunk: str) -> str:
    # a local model adds "where this came from" before you embed the chunk
    blurb = complete(
        f"In one sentence, situate this chunk in the document for search.\\n\\n"
        f"<doc>{doc[:4000]}</doc>\\n<chunk>{chunk}</chunk>",
        provider="local",            # free, overnight, embarrassingly parallel
    )
    return f"{blurb}\\n{chunk}"      # embed THIS, not the bare chunk`,
        },
      ],
    },
    {
      id: "p2-c2b",
      title: "The modern retrieval stack (what you actually import)",
      tag: "libraries, not algorithms",
      teaches: ["p2-o1"],
      blocks: [
        {
          kind: "p",
          text: "You will never implement BM25 or cosine similarity at work — every layer below is a maintained package. Knowing **which tool does which job** is the skill. This is the whole map, and the exercises use exactly these imports.",
        },
        {
          kind: "table",
          headers: ["Layer", "Its job", "What you import"],
          rows: [
            [
              "Keyword / sparse",
              "exact IDs, codes, rare jargon",
              "`rank_bm25` (3-line baseline) or `fastembed` SparseTextEmbedding('Qdrant/bm25')",
            ],
            [
              "Dense / semantic",
              "meaning, paraphrase",
              "`fastembed` TextEmbedding('BAAI/bge-small-en-v1.5') — local ONNX, no API key",
            ],
            [
              "Store + fusion",
              "holds both vectors, fuses the ranks",
              "`qdrant-client` — two Prefetch arms + FusionQuery(Fusion.RRF)",
            ],
            [
              "Rerank",
              "precision on the final handful",
              "`fastembed` TextCrossEncoder('BAAI/bge-reranker-base')",
            ],
            [
              "Chunking",
              "split without butchering sentences",
              "`langchain-text-splitters` RecursiveCharacterTextSplitter",
            ],
            ["Eval", "the merge gate", "`ragas` (LLM judge) + `rapidfuzz` for a fast offline gate"],
          ],
        },
        {
          kind: "callout",
          tone: "tip",
          title: "Qdrant with zero infrastructure",
          text: '`QdrantClient(":memory:")` runs the real client and the real API — fusion included — with no Docker and no network. Point it at `QdrantClient(url=...)` in production and **nothing else in your code changes**. That is exactly why you learn the client, not the algorithm.',
        },
        {
          kind: "code",
          title: "Hybrid search end to end — the code you actually write",
          code: `from fastembed import TextEmbedding, SparseTextEmbedding
from qdrant_client import QdrantClient, models

dense_model  = TextEmbedding("BAAI/bge-small-en-v1.5")   # meaning
sparse_model = SparseTextEmbedding("Qdrant/bm25")        # exact tokens
client = QdrantClient(":memory:")        # same API as a deployed server

client.create_collection("docs",
    vectors_config={"dense": models.VectorParams(size=384,
                    distance=models.Distance.COSINE)},
    sparse_vectors_config={"kw": models.SparseVectorParams()})

# index: every doc carries BOTH vectors
client.upsert("docs", points=[
    models.PointStruct(id=i, payload={"text": d},
        vector={"dense": dv.tolist(),
                "kw": models.SparseVector(indices=sv.indices.tolist(),
                                          values=sv.values.tolist())})
    for i, (d, dv, sv) in enumerate(zip(docs,
        dense_model.embed(docs), sparse_model.embed(docs)))])

# search: ONE call, two arms, fused server-side by RRF
hits = client.query_points("docs",
    prefetch=[models.Prefetch(query=dq, using="dense", limit=20),
              models.Prefetch(query=sq, using="kw",    limit=20)],
    query=models.FusionQuery(fusion=models.Fusion.RRF),   # <- the fusion
    limit=5, with_payload=True).points`,
        },
        {
          kind: "code",
          title: "Rerank the candidates (precision step)",
          code: `from fastembed.rerank.cross_encoder import TextCrossEncoder

reranker = TextCrossEncoder(model_name="BAAI/bge-reranker-base")
scores = list(reranker.rerank(query, candidates))       # cross-encoder scores
top5 = [c for c, _ in sorted(zip(candidates, scores),
                             key=lambda x: x[1], reverse=True)[:5]]

# Retrieve wide (recall), rerank narrow (precision). 20 -> 5 is the usual shape.`,
        },
        {
          kind: "callout",
          tone: "fix",
          title: "RRF: understand it, don't write it",
          text: "Reciprocal Rank Fusion scores each document as the sum of 1/(k+rank) across every ranked list it appears in (k≈60). That is all it is — worth understanding so you can reason about it. But you pass `Fusion.RRF` and the database does it. Hand-rolling fusion is how you get subtle ranking bugs nobody reviews.",
        },
      ],
    },
    {
      id: "p2-c3",
      title: "Chunking, minus the folklore",
      teaches: ["p2-o2"],
      blocks: [
        {
          kind: "p",
          text: "Everyone has a chunking opinion; few have data. Published results are genuinely mixed — fixed ~200-word chunks tie or beat fancy semantic chunking in several studies, while one clinical-domain paper found topic-aware splitting much better. The honest takeaway:",
        },
        {
          kind: "callout",
          tone: "tip",
          title: "Boring default, measured upgrades",
          text: "Start at ~512 tokens with 10–20% overlap. Split on document structure (headings) when there is structure. Adopt anything fancier **only after your eval scores say it helps on your data**.",
        },
        {
          kind: "code",
          title: "The boring default: ~512 tokens, ~15% overlap",
          code: `def chunk(text: str, size: int = 512, overlap: int = 75) -> list[str]:
    words, out, i = text.split(), [], 0
    step = size - overlap                    # overlap keeps facts from splitting
    while i < len(words):
        out.append(" ".join(words[i : i + size]))
        i += step
    return out

# Prefer splitting on real structure (headings) when the document has it;
# reach for semantic chunking ONLY if your eval scores say it earns its keep.`,
        },
      ],
    },
    {
      id: "p2-c4",
      title: "Enough scorekeeping to tune with",
      tag: "the number you tune against",
      teaches: ["p2-o3"],
      blocks: [
        {
          kind: "p",
          text: "You cannot tune retrieval without a number, so here is the minimum: two measurements that split every RAG failure in half. **Faithfulness** asks whether the answer is supported by what was retrieved — it catches hallucination, and it blames the *writer*. **Context recall** asks whether retrieval found the needed information at all, and blames the *librarian*. Which one moved tells you which half to open first.",
        },
        {
          kind: "callout",
          tone: "tip",
          title: "Fast and lexical here; judged and calibrated in Phase 3",
          text: "For this phase you need a gate that runs in seconds: a small set of golden questions, sliced by type, scored with deterministic string metrics (`rapidfuzz`). Deliberately crude — it catches “retrieval broke” instantly and costs nothing. **Phase 3 is where scorekeeping becomes a discipline**: real judges, calibration against your own labels, and a merge gate you can defend. Never report a lexical proxy as “faithfulness.”",
        },
        {
          kind: "code",
          title: "The fast gate you tune against in this phase",
          code: `from rapidfuzz import fuzz

def recall_nonllm(contexts: list[str], ground_truth: str) -> float:
    """Did retrieval surface the text the answer needs? Lexical, deterministic, free."""
    return max((fuzz.partial_ratio(ground_truth, c) for c in contexts), default=0.0) / 100

# Slice it, or an average will hide the failure that matters:
#   semantic    -> embeddings / chunking
#   exact       -> the keyword arm
#   unanswerable-> the abstain path
# Re-run this after EVERY retrieval change. Tuning by vibes is how you make it
# worse with confidence.`,
        },
      ],
    },
    {
      id: "p2-c5",
      title: "The fix-it playbook",
      tag: "interview gold",
      teaches: ["p2-o4"],
      blocks: [
        {
          kind: "p",
          text: "Interviewers don’t ask you to **describe** RAG anymore — they hand you a broken one. Work **backwards from the bad answer** and the failing stage reveals itself:",
        },
        {
          kind: "flow",
          title: "Walk it back-to-front",
          nodes: [
            {
              label: "Answer ignores its context?",
              sub: "writer problem: prompt, temperature, weak model",
            },
            {
              label: "Right doc missing from top-k?",
              sub: "is it even indexed? → ingestion bug",
            },
            {
              label: "Indexed but ranked low?",
              sub: "add keywords/hybrid, fix chunking, check embedding mismatch",
            },
            { label: "Retrieved but buried?", sub: "precision problem → add a reranker" },
          ],
        },
        {
          kind: "list",
          items: [
            "Sanity check #1: can you fetch the known-good doc by ID at all?",
            "Sanity check #2: are queries and documents embedded with **the same model**? (The classic silent killer.)",
            "Exact-string queries failing → you need keywords in the mix.",
            "Right chunk present but ignored → it’s drowning mid-context; rerank and trim.",
            "**Re-run the eval after every change. Tuning by vibes is how you make it worse with confidence.**",
          ],
        },
        {
          kind: "code",
          title: "The two-minute sanity check",
          code: `# 1. can you even fetch the known-good doc by ID?
assert store.get("doc-114") is not None, "ingestion bug - it's not indexed"

# 2. the classic silent killer: SAME embedding model for docs and queries?
assert doc_embedder.name == query_embedder.name, "mismatch -> recall craters"

# only after those pass do you tune chunking / hybrid / reranking -
# and re-run the eval after EVERY change, never by vibes.`,
        },
      ],
    },
  ],
  example: {
    title: "Field story: the vanishing statute",
    text: "A legal-tech team’s search nailed “cases about workplace retaliation” but couldn’t find the one case citing statute 18.2-57 — the embedding had shredded the number into noise. One afternoon adding a keyword index and fusing rankings, and recall on their exact-match test slice jumped from 0.41 to 0.93. The eval harness is what let them **see** the jump — and put it on a slide.",
  },
  exercises: [
    {
      id: "p2-e1",
      title: "The two-tier harness (build this one first)",
      repo: "phase2-retrieval/01-eval-harness",
      rung: "faded",
      task: "Write a 30-question golden set over your corpus — 15 meaning-based, 10 exact-match/jargon, 5 unanswerable (those test your “I don’t know” path). Score it two ways: a deterministic lexical tier that runs on every push, and an opt-in judged tier for the nightly run. Wrap tier 1 in pytest so a regression blocks the merge.",
      assesses: ["p2-o3"],
      solution: [
        "Name the lexical metrics `*_nonllm` on purpose — they measure string similarity, not faithfulness. Honest naming now saves an embarrassing slide later.",
        "Keep the heavy judged tier in an optional dependency group. A fast gate that can be broken by someone else’s transitive dependency is not a fast gate.",
        "Reward correct abstention on the unanswerable five — never penalize an honest “not in the docs.”",
        "Slice the results. “Recall 0.71” is useless; “recall 0.94 semantic / 0.32 exact” tells you to go add the keyword arm.",
      ],
      code: `# src/harness.py — tier 1: deterministic, offline, runs on every push
from rapidfuzz import fuzz

def score_row(row, answer: str, contexts: list[str]) -> dict:
    if row["slice"] == "unanswerable":              # the abstain path, judge-free
        return {"abstained": float(is_abstention(answer))}
    return {
        "answer_similarity_nonllm": fuzz.token_set_ratio(row["ground_truth"],
                                                         answer) / 100,
        "context_recall_nonllm": max(
            (fuzz.partial_ratio(row["ground_truth"], c) for c in contexts),
            default=0.0) / 100,
    }

def run(golden, pipeline) -> dict:
    rows = [{**r, **score_row(r, *pipeline(r["question"]))} for r in golden]
    return {"overall": mean_of(rows), "by_slice": grouped_means(rows)}

# tests/test_quality.py — the gate that blocks the merge (no model, no network)
def test_lexical_bars():
    s = run(load_golden("evals/golden.jsonl"), rag_pipeline)
    assert s["by_slice"]["exact"]["context_recall_nonllm"] >= 0.80
    assert s["by_slice"]["unanswerable"]["abstained"] == 1.0

# Tier 2 (real judges, calibration, per-slice gating) is Phase 3's whole job.`,
    },
    {
      id: "p2-e2",
      title: "Hybrid + rerank, with receipts",
      repo: "phase2-retrieval/02-hybrid-rerank",
      rung: "faded",
      task: "Add keyword search and a reranker to your Phase-1 pipeline. Measure context recall before and after with the harness — especially on the exact-match slice.",
      assesses: ["p2-o1"],
      needs: ["p1-o3"],
      solution: [
        "Fetch top-20 hybrid → rerank to top-5 → generate. Recall should jump on exact-match queries.",
        "Track token cost too — reranking usually **saves** money by sending fewer, better chunks downstream.",
      ],
      code: `# 1) index with BOTH vectors, 2) fuse, 3) rerank, 4) MEASURE.
from fastembed import TextEmbedding, SparseTextEmbedding
from fastembed.rerank.cross_encoder import TextCrossEncoder
from qdrant_client import QdrantClient, models

dense_model, sparse_model = (TextEmbedding("BAAI/bge-small-en-v1.5"),
                             SparseTextEmbedding("Qdrant/bm25"))
reranker = TextCrossEncoder(model_name="BAAI/bge-reranker-base")

def hybrid(query, k=20):
    dq = next(iter(dense_model.query_embed(query))).tolist()
    sv = next(iter(sparse_model.query_embed(query)))
    sq = models.SparseVector(indices=sv.indices.tolist(), values=sv.values.tolist())
    pts = client.query_points("docs",
        prefetch=[models.Prefetch(query=dq, using="dense", limit=k),
                  models.Prefetch(query=sq, using="kw",    limit=k)],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=k, with_payload=True).points
    return [p.payload["text"] for p in pts]

def hybrid_then_rerank(query, k=5):
    cands = hybrid(query, k=20)                      # wide: recall
    scores = list(reranker.rerank(query, cands))     # narrow: precision
    return [c for c, _ in sorted(zip(cands, scores),
                                 key=lambda x: x[1], reverse=True)[:k]]

# 4) the receipts: run your lesson-2.1 harness on each pipeline and diff,
#    sliced by question type. The exact-match slice is where hybrid pays off.
for name, fn in [("dense only", dense_only), ("hybrid", hybrid),
                 ("hybrid+rerank", hybrid_then_rerank)]:
    rows = build_dataset(load_golden("evals/golden.jsonl"),
                         lambda q: (generate(q, fn(q)), fn(q)))
    print(name, evaluate_nonllm(rows))`,
    },
    {
      id: "p2-e3",
      title: "Sabotage Saturday",
      repo: "phase2-retrieval/03-break-and-fix",
      rung: "faded",
      task: "Plant one bug in a working pipeline (mismatched embedding models, giant chunks, zero overlap) — or use the pre-bugged one in the repo — then hunt it with the playbook. Name which metric moved and why.",
      assesses: ["p2-o2", "p2-o4"],
      needs: ["p1-o3"],
      solution: [
        "Mismatched embeddings crater **context recall**. Bloated chunks dent **precision**. A lazy prompt shows up in **faithfulness**.",
        "That bug→metric mapping, said out loud, is a strong interview answer all by itself.",
      ],
      code: `# The bug is almost never where the symptom is. Work back-to-front.
# Symptom: nonsense retrieval, nothing crashed, context_recall cratered.

# The #1 real-world cause: the index and the query used DIFFERENT embedders.
# Same vector size => no exception => silent garbage.
class RAG:
    def __init__(self, docs, embed):
        self.embed = embed                      # ONE embedder, stored once
        self.client = QdrantClient(":memory:")
        self.client.create_collection("docs",
            vectors_config=models.VectorParams(size=384,
                distance=models.Distance.COSINE))
        self.client.upsert("docs", points=[
            models.PointStruct(id=i, vector=self.embed(d), payload={"text": d})
            for i, d in enumerate(docs)])

    def retrieve(self, query, k=3):
        qv = self.embed(query)                  # <- the SAME embedder. Always.
        pts = self.client.query_points("docs", query=qv, limit=k,
                                       with_payload=True).points
        return [p.payload["text"] for p in pts]

# The regression guard that would have caught it originally:
def test_mixing_embedders_breaks_retrieval():
    rag = RAG(DOCS, embed=model_a)
    good = rag.retrieve("when was the invoice paid?")
    rag.embed = model_b                          # simulate the drift
    assert good != rag.retrieve("when was the invoice paid?")

# In production also record the model name on the collection and refuse to
# query on mismatch -- then re-embed the corpus when you change models.`,
    },
    {
      id: "p2-e4",
      title: "Contextual chunks, free of charge",
      repo: "phase2-retrieval/04-contextual-chunks",
      rung: "faded",
      task: "Implement chunk contextualization using a local model as the batch worker (it’s free). Compare retrieval failure rate against the naive version on your golden set.",
      assesses: ["p2-o2"],
      needs: ["p1-o1"],
      solution: [
        "Prompt: “In one sentence, situate this chunk within the document” → prepend to the chunk → re-embed.",
        "It’s embarrassingly parallel; an overnight Ollama run costs exactly nothing.",
      ],
      code: `from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import OpenAI

# split with the library everyone uses (respects paragraph/sentence bounds)
splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=75,
    separators=["

", "
", ". ", " ", ""])
chunks = splitter.split_text(doc)

# the batch worker is a FREE local model -- this is why the trick is cheap
ollama = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

PROMPT = ("In one short sentence, situate this chunk within the document so it "
          "can be found by search. Reply with the sentence only.
"
          "<document>
{doc}
</document>
<chunk>
{chunk}
</chunk>")

def contextualize(doc, chunk):
    r = ollama.chat.completions.create(model="qwen3.5:9b", temperature=0,
        messages=[{"role": "user",
                   "content": PROMPT.format(doc=doc[:4000], chunk=chunk)}])
    return r.choices[0].message.content.strip() + "
" + chunk   # embed THIS

contextual = [contextualize(doc, c) for c in chunks]   # embarrassingly parallel

# Then prove it: index both variants and compare context_recall on the SAME
# golden set. Anthropic measured ~49% fewer retrieval failures from this alone.`,
    },
    {
      id: "p2-e5",
      title: "Blank editor: the 20-minute triage, on someone else’s corpus",
      rung: "independent",
      task: "Empty directory. Take a corpus you have never indexed — your own notes, a downloaded standards document, a repo’s docs folder — and in one sitting write a script that answers, in order: is the known-good document indexed at all, are queries and documents embedded by the same model, does the right chunk make top-20, and does it make top-5. Ten questions is enough. Then write three sentences naming which stage is worst and what you would change first. No harness from exercise 1 to start from — the point is that you can build the diagnostic, not run it.",
      assesses: ["p2-o3", "p2-o4"],
      needs: ["p1-o3"],
      solution: [
        "Your script reports per-stage numbers, not one score. A single “accuracy: 0.6” cannot tell you whether to fix ingestion or add a reranker, and producing it is the mistake this task exists to catch.",
        "You checked embedder identity before tuning anything. Everyone agrees this is the first check and almost nobody writes it down; a script that asserts it is the difference between knowing the playbook and having it.",
        "The unanswerable questions are in there, and abstention counts as correct. If your ten questions all have answers, you have built a harness that rewards confident nonsense.",
        "Your three sentences name a stage and a change, in that order. “Retrieval is bad, I’ll try a better embedding model” is the vibes-tuning this phase spent four exercises arguing against; “the exact-match slice recalls 0.3 while semantic recalls 0.9, so the keyword arm is missing” is the answer that gets you hired.",
        "It runs on a corpus with no golden set waiting for it. That is the actual job — the tidy `evals/golden.jsonl` in the companion repo was a scaffold, and this is the first time you have had to invent the questions too.",
      ],
    },
  ],
  checkpoint: [
    {
      id: "p2-q1",
      q: "Why does pure vector search miss exact identifiers, and what’s the fix?",
      a: "Tokenizers shred IDs and codes into sub-tokens with no stable meaning, so there’s no clean vector neighborhood. Fix: keyword search (BM25) fused with dense results, then a reranker for precision.",
    },
    {
      id: "p2-q2",
      q: "You can only afford two metrics. Which, and what does each blame?",
      a: "Faithfulness (blames the writer — catches hallucination) and context recall (blames the librarian — did retrieval find it). Together they split every failure into “generation” or “retrieval,” which is debugging question #1.",
    },
    {
      id: "p2-q3",
      q: "Your overall recall is 0.71 and you have one afternoon. What do you look at?",
      a: "The per-slice breakdown, not the average. Recall that is strong on paraphrase questions and terrible on identifier questions is a missing keyword arm — a couple of hours of wiring. A uniform 0.71 across every slice is a different bug entirely (chunking, or an embedding mismatch between index and query). Averages hide the cheap fix.",
    },
    {
      id: "p2-q4",
      q: "Make the case for and against GraphRAG in one breath.",
      a: "For: multi-hop and corpus-wide questions (“trends across all filings”) that chunk retrieval structurally can’t answer. Against: heavy build/run cost when hybrid + rerank + contextual chunks already pass your eval bar for ordinary Q&A.",
    },
  ],
  workshop: {
    id: "w1",
    title: "Workshop · Ship a real RAG service",
    subtitle: "Everything from Phases 1–2, wired into one running system you can curl.",
    repo: "workshops/assistant",
    assesses: ["p2-o1", "p2-o2", "p2-o3", "p2-o4"],
    needs: ["p1-o1", "p1-o2", "p1-o3"],
    blocks: [
      {
        kind: "p",
        text: "Time to stop reading and build. This is the first checkpoint where the pieces become a **system**: a small FastAPI service that ingests a real corpus, retrieves with hybrid + rerank, answers with citations, refuses when it should, and proves its own quality with an eval gate. Nothing here is new — it is Phases 1 and 2 assembled and made to run.",
      },
      {
        kind: "p",
        text: "The `before/` folder is a skeleton with `TODO`s and passing-but-empty tests; `after/` is the finished reference. Resist opening `after/` until your own version is stuck.",
      },
      {
        kind: "callout",
        tone: "tip",
        title: "Why Qdrant for this build",
        text: "We use **Qdrant** as the vector store: one `docker run` to start, and it does **native hybrid search** (dense + sparse in one query) so the Phase-2 lesson stays first-class instead of bolted on. Everything you write stays behind your own `Store` interface, so swapping in pgvector later is a two-function change — exactly the adapter habit from Phase 1.",
      },
      {
        kind: "code",
        title: "The whole stack comes up with one command",
        code: `# docker-compose.yml — Qdrant + the service, zero cloud accounts
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports: ["6333:6333"]
  ollama:                       # embeddings + a small local generator = $0
    image: ollama/ollama:latest
    ports: ["11434:11434"]
  api:
    build: .
    ports: ["8000:8000"]
    depends_on: [qdrant, ollama]
    environment: [QDRANT_URL=http://qdrant:6333]

# then:  make ingest  &&  make eval  &&  curl localhost:8000/ask -d '{"q": "..."}'`,
      },
      {
        kind: "flow",
        title: "What you’re building",
        nodes: [
          { label: "Ingest", sub: "chunk → contextualize → embed → upsert" },
          { label: "/ask endpoint", sub: "FastAPI" },
          { label: "Hybrid + rerank", sub: "Qdrant native, top-20 → 5" },
          { label: "Grounded answer", sub: "citations + abstain path" },
          { label: "Eval gate", sub: "RAGAS in CI" },
        ],
      },
      {
        kind: "code",
        title: "The seam you implement (before/store.py)",
        code: `class Store(Protocol):
    def upsert(self, chunks: list[Chunk]) -> None: ...
    def hybrid_search(self, query: str, k: int = 20) -> list[Chunk]: ...

class QdrantStore:                       # <- your job in the workshop
    def hybrid_search(self, query, k=20):
        # TODO: dense vector + sparse (BM25) in ONE Qdrant query,
        #       fuse server-side, return top-k. Then rerank to 5 upstream.
        ...`,
      },
    ],
    deliverables: [
      {
        id: "w1-d1",
        text: "`docker compose up` brings the whole stack online with **no API keys** (Ollama for embeddings + generation)",
      },
      {
        id: "w1-d2",
        text: "`POST /ask` returns a grounded answer **with citations**, and abstains (“not in the docs”) on unanswerable questions",
      },
      {
        id: "w1-d3",
        text: "Retrieval is **hybrid + reranked** — verified by a recall jump on the exact-match slice of your golden set",
      },
      {
        id: "w1-d4",
        text: "`make eval` runs the fast lexical gate over the golden slices and **CI fails** on a regression — Phase 3 upgrades this gate to a judged one",
      },
      {
        id: "w1-d5",
        text: "The vector store lives behind a `Store` interface — you can articulate exactly what changes to move to pgvector",
      },
    ],
    stretch: [
      "Add contextual retrieval (the Phase-2 local-model batch job) and measure the recall delta.",
      "Swap QdrantStore for a PgVectorStore behind the same interface; confirm the eval still passes.",
      "Add a `/ask` streaming variant (SSE) so answers render token-by-token.",
    ],
  },
  resources: [
    { label: "RAGAS docs", url: "https://docs.ragas.io" },
    {
      label: "Anthropic — Contextual Retrieval",
      url: "https://www.anthropic.com/news/contextual-retrieval",
    },
    { label: "Langfuse (OSS tracing + evals)", url: "https://langfuse.com" },
    { label: "Arize Phoenix", url: "https://phoenix.arize.com" },
    {
      label: "Qdrant — hybrid search docs",
      url: "https://qdrant.tech/documentation/concepts/hybrid-queries/",
    },
    {
      label: "“Lost in the Middle” (Liu et al.)",
      url: "https://arxiv.org/abs/2307.03172",
    },
  ],
};
