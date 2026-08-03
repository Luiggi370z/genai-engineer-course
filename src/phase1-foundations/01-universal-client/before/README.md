# 1.1 Universal client

**Goal.** Build one client that reaches five providers — OpenAI, Anthropic, Google, Ollama and MLX — behind a single call, with `complete`, `stream`, `call_tool` and `extract` each normalized to one shape, so swapping models is config, not code.
**Prerequisite.** none — this is the first build of the course.
**Effort.** ~60 min to green on the fast tests · +20 min for the integration tier · ~100 min realistic first pass.

## Do this

```bash
make setup && make test     # 12 failing tests — read them, they are the spec
$EDITOR src/client.py       # fill the provider table and the four capabilities
make check                  # green: ruff + pyright + pytest, all offline
```

## What the first failure means

`test_every_provider_is_configured_not_hardcoded` fails with a `KeyError` because the `PROVIDERS` table is empty. It is telling you to describe each provider as data — a `base_url`, an API key, a model string — so that four of the five keys (`"gpt"`, `"gemini"`, `"local"`, `"mlx"`) can share one OpenAI-compatible adapter and adding a provider becomes a config change, not a new code path.

## Done when

- [ ] `make check` is green (lint, types, fast tests).
- [ ] Tool calls from the OpenAI wire and the Anthropic wire both come back as the same `ToolCall(name, args)` — `test_tool_calls_normalize_to_one_shape_across_providers` pins this.
- [ ] `extract` raises `ValueError` naming the missing field when a reply skips a required key (`test_extract_refuses_a_reply_missing_required_fields`).

## Stuck?

1. There are only two adapters to write: everything except `"claude"` rides the OpenAI wire format. Start with `complete` on that path and four providers pass at once.
2. Build your SDK clients only through `_openai_client` / `_anthropic_client` — the tests monkeypatch those seams with fakes. For streams, skip chunks with empty `choices` or a `None` delta; for Anthropic, concatenate the `type == "text"` content blocks and stream via `messages.stream(...).text_stream`.

## Going further (optional integration lane)
`make test-integration` runs the same four calls against a real local model via Ollama. Needs Ollama serving `qwen3.5:9b` — ~5 GB model pull, free on local Ollama. Skippable: the fast tier already proves the normalization.
