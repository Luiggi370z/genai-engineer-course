# ADR-0006 — A holdback window on the output stream

**Status:** accepted

## Context

`/ask` screens its answer before returning it. `/ask/stream` originally yielded
every chunk as the composer produced it and screened the joined text at the end.
Those are not the same guarantee. In the streaming path the gate fired *after*
delivery: the PII was already rendered in the caller's browser and written to
every proxy log on the way. The `done` event's redaction notice asked the client
to un-see it.

Two obvious fixes, both bad on their own. Buffer the whole answer and streaming
is gone — the feature exists to reduce time-to-first-token. Keep emitting and the
gate is decorative.

## Decision

Screen the accumulated answer on every chunk, and release only the prefix that
sits at least `HOLDBACK_CHARS` (256) behind the head of the buffer.

The bound is what makes it sound. Every pattern `guardrails.output_ok` can match
spans fewer than 256 characters, so a match that *starts* inside a released
prefix must already be complete — and therefore already caught — before that
prefix is released. Nothing unscreened crosses the boundary, and the client still
receives a long answer progressively.

`ASSISTANT_STREAM_MODE` selects `safe-buffered` (default) or `raw`. `raw` is the
original emit-then-judge behavior, kept because a test that pins the leak
side-by-side with the fix teaches more than a deleted branch, and documented as
local-only.

## Alternatives considered

Full buffering (correct, and throws away the feature). A rolling redactor that
rewrites PII in flight instead of blocking (diverges from `/ask`, which blocks —
two gates with two verdicts is worse than one gate). Screening each chunk in
isolation (catches nothing: a pattern straddling a chunk boundary is invisible to
both halves). Trusting the model not to emit PII (not a control).

## Consequences

An answer shorter than 256 characters arrives in a single frame, and every answer
reaches the client 256 characters behind generation. Both are accepted and
measurable, and `tier.stream` on `/health` reports which mode is live so an
operator can tell from outside the process. Adding an output pattern that can
match a longer span requires raising the window — `test_stream.py` asserts the
bound rather than trusting it.
