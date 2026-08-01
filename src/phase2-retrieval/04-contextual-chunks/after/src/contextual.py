"""Contextual retrieval: prepend a "where this came from" line BEFORE embedding.

Anthropic measured ~49% fewer retrieval failures from this one trick. The work is
embarrassingly parallel and needs only a small model, so it runs free on Ollama
overnight — that's the whole economic argument.

Splitting uses `langchain-text-splitters` (RecursiveCharacterTextSplitter), the
splitter real projects use. We don't hand-roll chunking here either.
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
    """Split with LangChain's recursive splitter — respects paragraph/sentence bounds."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_text(text)


def local_summarizer(model: str = "qwen3.5:8b") -> Summarizer:
    """A FREE summarizer on Ollama via the OpenAI-compatible endpoint."""
    from openai import OpenAI

    client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

    def summarize(prompt: str) -> str:
        resp = client.chat.completions.create(
            model=model,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        return (resp.choices[0].message.content or "").strip()

    return summarize


def contextualize(doc: str, chunk: str, summarize: Summarizer) -> str:
    """Return the chunk with a one-line context blurb prepended. Embed THIS."""
    blurb = summarize(PROMPT.format(doc=doc[:4000], chunk=chunk)).strip()
    return f"{blurb}\n{chunk}"


def contextualize_all(doc: str, chunks: list[str], summarize: Summarizer) -> list[str]:
    """Batch job: cheap, parallelizable, run it offline on a local model."""
    return [contextualize(doc, c, summarize) for c in chunks]
