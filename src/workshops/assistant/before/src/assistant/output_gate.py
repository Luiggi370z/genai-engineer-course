"""The outbound trust boundary — nothing leaves before the gate has seen it.

`screening.py` guards what comes *in*. This guards what goes *out*, and the
streaming case is where that gets interesting.

The naive streaming shape yields each chunk as it arrives and screens the joined
answer at the end. That gate cannot do its job: by the time it fires, the PII is
already rendered in the caller's browser and sitting in their proxy logs. A
`done` event announcing "actually that was redacted" is a notification, not a
control.

Buffering the whole answer fixes it and throws away streaming. The middle is a
**holdback window**: keep the last `HOLDBACK_CHARS` characters back, screen the
accumulated text on every chunk, and release only the prefix that is far enough
behind the head. The argument only works if no pattern the gate can match spans
more than `HOLDBACK_CHARS` characters — then a match that *starts* inside the
released prefix must already be complete, and therefore already caught, before
that prefix goes out.

That premise used to be a comment claiming a round number was "far more than
enough". It was wrong: an unbounded `+` in the email pattern could match a span
of any length, and a long enough local part pushed the start of the address out
of the window and onto the wire. The window is now *derived* from the patterns
instead of asserted over them — every entry in `guardrails.PII` declares the
longest text it can match, and this module takes the maximum. Adding a pattern
that can match further automatically widens the window, and a pattern that
cannot state a bound cannot be added at all.

The cost is honest and bounded: the caller sees the answer `HOLDBACK_CHARS`
characters later than they otherwise would, and an answer shorter than the window
arrives in a single frame. That is the price of a gate that actually gates, and
`ASSISTANT_STREAM_MODE=raw` is available for local work where it is not worth
paying — documented as local-only, because with it the gate becomes a
notification again.

The other terminal event here is `truncated`. A model that dies halfway through
leaves a grammatical fragment that reads like a whole answer; presenting it as
one is its own kind of dishonesty, so the gate distinguishes "this is the answer"
from "this is as far as the answer got".
"""
from __future__ import annotations

from collections.abc import Iterator

from assistant import guardrails
from assistant.composers import StreamTruncated

SAFE_BUFFERED = "safe-buffered"
RAW = "raw"

#: The window, derived from the patterns rather than guessed ahead of them: the
#: longest span any `guardrails.PII` entry can match. Release a character sooner
#: than this and a match could still form behind it.
HOLDBACK_CHARS = max(p.max_span for p in guardrails.PII)

REDACTION = "[redacted: output failed the safety gate]"


def gated_chunks(
    chunks: Iterator[str], mode: str = SAFE_BUFFERED
) -> Iterator[tuple[str, str]]:
    """TODO 1: screen a stream on its way out.

    Yield `("chunk", text)` for every span cleared to leave the process, then
    exactly one terminal event:

      * `("done", answer)` — the whole answer arrived and passed
        `guardrails.output_ok`;
      * `("blocked", REDACTION)` — it did not pass;
      * `("truncated", partial)` — the source raised `StreamTruncated`, meaning
        it stopped mid-answer.

    `mode == RAW` is the naive shape and is written for you in `_raw` below —
    read it first, then build the default so the difference is concrete.

    For SAFE_BUFFERED, keep two pieces of state: the accumulated `buffer` and how
    many characters you have `released`. On every incoming chunk:

      * append it to the buffer and re-screen the WHOLE buffer — a pattern can
        straddle a chunk boundary, so screening chunks individually catches
        nothing;
      * on failure, yield ("blocked", REDACTION) and stop. What you already
        released is clean by construction; the client still discards it;
      * otherwise compute `cut = len(buffer) - HOLDBACK_CHARS` and, if that is
        ahead of `released`, yield `buffer[released:cut]` and move `released` up.

    When the source is exhausted, screen once more, flush whatever is still held
    back, and yield ("done", buffer).

    Wrap the loop in `try: ... except StreamTruncated:` and remember that it
    happened. The tail still gets screened and flushed — text that already left
    the model is text you are responsible for — but the terminal event becomes
    `("truncated", buffer)` instead of `("done", buffer)`. Ending a died-early
    stream with `done` is how a fragment gets served as a finished answer.

    Two tests to hold yourself to: a stream whose LAST chunk completes an email
    address must emit no chunk containing it, and the window you rely on is
    `HOLDBACK_CHARS`, which is derived from `guardrails.PII` rather than picked.
    Do not hardcode a number here.
    """
    raise NotImplementedError


def _raw(chunks: Iterator[str]) -> Iterator[tuple[str, str]]:
    """Emit first, judge later. Local-only: the verdict arrives after the content
    it was supposed to withhold, which is exactly the failure the default mode
    exists to prevent. Kept because seeing the two side by side is the lesson."""
    parts: list[str] = []
    truncated = False
    try:
        for chunk in chunks:
            parts.append(chunk)
            yield "chunk", chunk
    except StreamTruncated:
        truncated = True
    answer = "".join(parts)
    if not guardrails.output_ok(answer):
        yield "blocked", REDACTION
        return
    yield ("truncated" if truncated else "done"), answer
