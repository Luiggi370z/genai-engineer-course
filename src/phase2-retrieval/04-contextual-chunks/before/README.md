# 2.4 Contextual chunks

**Goal.** Implement contextual retrieval: split documents with the standard
LangChain splitter, then prepend one cheap model-written sentence to each chunk
before embedding. Anthropic measured ~49% fewer retrieval failures from that one
sentence — and on a local model it costs $0.
**Prerequisite.** 2.2 Hybrid + rerank (this improves what your retriever indexes).
**Effort.** ~25 min · gentle.

## Do this

```bash
make setup && make test     # 3 failing tests — read them, they are the spec
$EDITOR src/contextual.py   # TODOs 1-4: split, local summarizer, contextualize one chunk + all
make check                  # green: ruff + pyright + pytest, all offline
```

## What the first failure means

`test_split_uses_the_library_and_respects_size` fails because `split` isn't
built. It wants `RecursiveCharacterTextSplitter` from `langchain-text-splitters`
— the splitter real projects actually use — honoring the given `chunk_size` and
`chunk_overlap`. Don't hand-roll chunking.

## Done when

- [ ] `make check` is green (lint, types, fast tests).
- [ ] `test_context_is_prepended_before_the_chunk` passes: the blurb is the
      first line and the original chunk is intact below it.
- [ ] `contextualize_all` preserves chunk count and order — it's the cheap batch
      job you'd run overnight over a whole corpus.

## Stuck?

1. Half the TODOs are one or two lines: construct the splitter with the given
   sizes and call its text-splitting method; the batch version just maps the
   single-chunk version over the list.
2. `contextualize` formats `PROMPT` with the doc and chunk, calls
   `summarize(...)`, and returns blurb, newline, chunk. `local_summarizer` is an
   OpenAI client pointed at `base_url="http://localhost:11434/v1"` with
   `temperature=0` — Ollama speaks the OpenAI API.

## Going further (optional integration lane)
`make test-integration` runs `contextualize` against a real local summarizer on
Ollama. Needs `ollama serve` with a small model pulled (the default is an 8B —
a few GB of disk, fine on a laptop, no API cost). Skippable: the fast tier
already proves the logic with an injected summarizer.
