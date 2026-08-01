# 1.3 Structured extraction

**Goal.** Extract a typed `Invoice` from messy text with `response_model` — a decoder-enforced constraint, not a "reply with JSON" plea — then batch it and measure the violation rate, the number the hosted-vs-laptop shoot-out compares.
**Prerequisite.** 1.1 Universal client (you built `extract` and checked schemas by hand; Instructor is that idea productized).
**Effort.** ~30 min · gentle.

## Do this

```bash
make setup && make test     # 4 failing tests — read them, they are the spec
$EDITOR src/extract.py      # build_client, extract_invoice, extract_all, violation_rate
make check                  # green: ruff + pyright + pytest, all offline
```

## What the first failure means

`test_extraction_asks_for_the_schema_not_for_json_in_prose` fails because `extract_invoice` isn't built. It asserts that the client received `response_model=Invoice` — the schema must travel as a constraint in the call, not as a suggestion in the prompt. Taking the client as a parameter is what makes that checkable without a live model.

## Done when

- [ ] `make check` is green (lint, types, fast tests).
- [ ] A text the model cannot shape is counted, not crashed — `test_a_case_the_model_cannot_shape_is_counted_not_crashed` pins the `(invoices, violations)` split and the 0.5 rate.
- [ ] `violation_rate([], [])` returns `0.0` instead of dividing by zero.

## Stuck?

1. The `Invoice` model is already written — notice its constraints (`min_length`, `ge`) live in the type, not the prompt. Your job is plumbing: get that model into the call, and the failures into a list instead of up the stack.
2. `build_client` wraps an OpenAI-compatible client with Instructor (`instructor.from_openai(...)`, JSON mode for Ollama) and returns its `.chat.completions`; `extract_invoice` passes `response_model=Invoice`; `extract_all` catches per-text exceptions and appends the text to `violations`.

No integration lane: the extractor is injected, so the fast tests exercise the real extraction path against a fake — the whole lesson runs offline.
