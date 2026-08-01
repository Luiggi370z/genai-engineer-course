# 2.4 Contextual chunks — reference

LangChain `RecursiveCharacterTextSplitter` for splitting + a one-line context blurb prepended before embedding (~49% fewer retrieval failures per Anthropic). The summarizer is injected, so tests are offline; `make test-integration` runs the real local model on Ollama.
