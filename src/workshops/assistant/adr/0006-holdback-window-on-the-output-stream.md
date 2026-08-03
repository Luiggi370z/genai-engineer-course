# ADR-0006 — A holdback window on the output stream

**Status:** accepted (amended — see "Amendment: the bound is derived, not declared")

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
sits at least `HOLDBACK_CHARS` behind the head of the buffer.

The bound is what makes it sound. If no pattern `guardrails.output_ok` can match
spans more than `HOLDBACK_CHARS` characters, then a match that *starts* inside a
released prefix must already be complete — and therefore already caught — before
that prefix is released. Nothing unscreened crosses the boundary, and the client
still receives a long answer progressively.

`ASSISTANT_STREAM_MODE` selects `safe-buffered` (default) or `raw`. `raw` is the
original emit-then-judge behavior, kept because a test that pins the leak
side-by-side with the fix teaches more than a deleted branch, and documented as
local-only.

## Amendment: the bound is derived, not declared

The first version of this decision set `HOLDBACK_CHARS = 256` and asserted in a
comment that every pattern was "far shorter". That assertion was false. The
email pattern was:

```python
re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
```

`+` has no maximum. An address with a 325-character local part began *before* the
window, so by the time the closing `.com` made the match recognisable, 69
characters of it had already been released as safe. The soundness argument above
was correct; its premise was not, and nothing in the system checked the premise.
The one test that looked like it did built a 194-character email by hand and
called it maximal.

Two changes close it:

1. **Every output pattern declares its maximum span** (`guardrails.Bounded`).
   The email pattern is now bounded to RFC-shaped limits — 64 characters of
   local part, 63 per domain label, at most four labels, so 384 characters. An
   over-long local part is still detected, because the last 64 characters of it
   still match; only the *span* is bounded, not the detection.
2. **The window is computed from those declarations**:
   `HOLDBACK_CHARS = max(p.max_span for p in guardrails.PII)`. Adding a pattern
   that can match further widens the window automatically. A pattern that cannot
   state a bound cannot be added.

`test_stream.py` proves each declaration against the compiled regex using the
`re` parser's own width calculation, so a pattern that outgrows its declared
bound fails the suite. The proof lives in the test rather than in the gate: it
reaches into a private module, which is acceptable where a future Python breaks
it loudly and unacceptable on the request path.

The general lesson is worth more than the fix. A safety property written in a
comment is enforced by nobody. This one is now enforced by arithmetic.

## Alternatives considered

Full buffering (correct, and throws away the feature). A stateful incremental
DLP scanner that tracks partial-match state per chunk (strictly more general,
and for a bounded pattern set it computes exactly the window derived above, at
considerably more complexity). A rolling redactor that rewrites PII in flight
instead of blocking (diverges from `/ask`, which blocks — two gates with two
verdicts is worse than one gate). Screening each chunk in isolation (catches
nothing: a pattern straddling a chunk boundary is invisible to both halves).
Trusting the model not to emit PII (not a control).

## Consequences

An answer shorter than `HOLDBACK_CHARS` arrives in a single frame, and every
answer reaches the client that many characters behind generation. The window
widened from 256 to 384 when the bound became real, which is the honest price of
the guarantee the original number was only claiming. Both are accepted and
measurable, and `tier.stream` on `/health` reports which mode is live so an
operator can tell from outside the process.
