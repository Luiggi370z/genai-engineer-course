# 1.2 Token & cost meter — reference

`count_openai` (tiktoken pre-flight) + `cost(model, usage)` computed from the
`usage` object, including cached tokens. `make check` passes offline.
