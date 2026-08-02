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
behind the head. Any pattern the gate can match spans at most `HOLDBACK_CHARS`
characters, so a match that *starts* inside the released prefix must already be
complete — and therefore already caught — before that prefix is released.

The cost is honest and bounded: the caller sees the answer `HOLDBACK_CHARS`
characters later than they otherwise would, and an answer shorter than the window
arrives in a single frame. That is the price of a gate that actually gates, and
`ASSISTANT_STREAM_MODE=raw` is available for local work where it is not worth
paying — documented as local-only, because with it the gate becomes a
notification again.
"""
from __future__ import annotations

from collections.abc import Iterator

from assistant import guardrails

SAFE_BUFFERED = "safe-buffered"
RAW = "raw"

# Must be at least as long as the longest span `guardrails.output_ok` can match.
# The patterns it uses (SSNs, email addresses) are far shorter; 256 leaves room
# for a new pattern without silently breaking the guarantee. Adding a pattern
# that can match longer than this window means raising it or buffering fully.
HOLDBACK_CHARS = 256

REDACTION = "[redacted: output failed the safety gate]"


def gated_chunks(
    chunks: Iterator[str], mode: str = SAFE_BUFFERED
) -> Iterator[tuple[str, str]]:
    """TODO 1: screen a stream on its way out.

    Yield `("chunk", text)` for every span cleared to leave the process, then
    exactly one terminal event: `("done", answer)` when the whole answer passed
    `guardrails.output_ok`, or `("blocked", REDACTION)` when it did not.

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

    Test it with a stream whose LAST chunk completes an email address: no emitted
    chunk may contain it.
    """
    raise NotImplementedError


def _raw(chunks: Iterator[str]) -> Iterator[tuple[str, str]]:
    """Emit first, judge later. Local-only: the verdict arrives after the content
    it was supposed to withhold, which is exactly the failure the default mode
    exists to prevent. Kept because seeing the two side by side is the lesson."""
    parts: list[str] = []
    for chunk in chunks:
        parts.append(chunk)
        yield "chunk", chunk
    answer = "".join(parts)
    if not guardrails.output_ok(answer):
        yield "blocked", REDACTION
        return
    yield "done", answer
