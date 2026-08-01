"""TODO: implement contextual retrieval with real libraries.

- split(text, size, overlap): use langchain_text_splitters.RecursiveCharacterTextSplitter
  (don't hand-roll chunking — this is the splitter real projects use).
- local_summarizer(model): return a callable backed by Ollama's OpenAI-compatible
  endpoint (base_url="http://localhost:11434/v1", api_key="ollama", temperature=0).
- contextualize(doc, chunk, summarize): PREPEND the one-line blurb to the chunk.
- contextualize_all(...): map it over all chunks (the cheap overnight batch job).

Reference: ../after/src/contextual.py
"""
from __future__ import annotations

from collections.abc import Callable

Summarizer = Callable[[str], str]

PROMPT = (
    "In one short sentence, situate this chunk within the document so it can be "
    "found by search. Reply with the sentence only.\n"
    "<document>\n{doc}\n</document>\n<chunk>\n{chunk}\n</chunk>"
)


def split(text: str, chunk_size: int = 512, chunk_overlap: int = 75) -> list[str]:
    raise NotImplementedError  # TODO 1


def local_summarizer(model: str = "qwen3.5:9b") -> Summarizer:
    raise NotImplementedError  # TODO 2


def contextualize(doc: str, chunk: str, summarize: Summarizer) -> str:
    raise NotImplementedError  # TODO 3


def contextualize_all(doc: str, chunks: list[str], summarize: Summarizer) -> list[str]:
    raise NotImplementedError  # TODO 4
