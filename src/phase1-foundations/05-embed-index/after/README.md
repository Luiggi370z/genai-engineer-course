# 1.5 Embed & index — reference

Local embeddings + a numpy cosine index + `search(query, k)`. The embedder is injected,
so the offline tests drive `search` itself with vectors they chose; the live semantic
demo is in `__main__` and needs Ollama.
