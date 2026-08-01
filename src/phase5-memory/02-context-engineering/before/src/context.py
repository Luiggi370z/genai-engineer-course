"""Context engineering: the window is a budget, not a bag.

A long agent run does not fail because the model is weak. It fails because by step
twelve the window is a landfill of stale tool output and the actual instruction is
buried. Four moves, applied deliberately at every step:

    keep      pin the constraints and the task — they never get evicted
    compress  fold finished turns into a summary you have TESTED
    evict     drop what a newer line supersedes
    park      leave the bulk in the store, recall it on demand

Given: the `Line` and `Context` records, both counters, the summary-drift check and
the poison-removal helper. Yours: the four moves and the assembly that spends the
budget. Run `make test` first — the failures are the spec.

Two design decisions carry the whole lesson:

  * every line names its `source`, so a wrong answer is traceable to the line that
    caused it — and that line is deletable. This is the only real defence against
    context poisoning.
  * the token counter is injected. Production counts with the model's own tokenizer;
    tests count with a deterministic stand-in and stay hermetic.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field

#: Anything that turns text into a token count. `tiktoken_counter()` in production.
Counter = Callable[[str], int]

#: Anything that turns many lines of text into one shorter line.
Summarizer = Callable[[str], str]

_WORD = re.compile(r"[\w']+|[^\w\s]")


class BudgetError(ValueError):
    """Pinned content alone exceeds the budget: a design bug, not a runtime hiccup."""


@dataclass(frozen=True)
class Line:
    """One unit of context, with the provenance that makes it auditable."""

    id: str
    text: str
    source: str
    pinned: bool = False
    score: float = 0.0
    supersedes: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Context:
    """The assembled prompt context, plus the receipt for how it was spent."""

    lines: list[Line]
    tokens: int
    budget: int
    parked: list[Line]

    @property
    def sources(self) -> list[str]:
        return [line.source for line in self.lines]

    def render(self) -> str:
        """What actually goes in the prompt. The source travels with the claim."""
        return "\n".join(f"[{line.source}] {line.text}" for line in self.lines)

    def from_source(self, source: str) -> list[Line]:
        """Every line that came from one place — how you trace a poisoned claim."""
        return [line for line in self.lines if line.source == source]


# ------------------------------------------------------------------- counters
def word_counter(text: str) -> int:
    """A deterministic stand-in for a real tokenizer: words and punctuation.

    It is not the model's tokenizer and does not pretend to be. It is stable across
    machines and needs no network, which is what a fast tier requires. Anywhere the
    number is used to spend real money, use `tiktoken_counter()`.
    """
    return len(_WORD.findall(text))


def tiktoken_counter(encoding: str = "o200k_base") -> Counter:
    """The real thing (GPT-4o/5.x encoding). Downloads the BPE file on first use."""
    import tiktoken

    enc = tiktoken.get_encoding(encoding)
    return lambda text: len(enc.encode(text))


# -------------------------------------------------------------------- the moves
def dedupe(lines: Iterable[Line], threshold: float = 92.0) -> list[Line]:
    """Drop repeats of the same claim, keeping the first (highest-ranked) copy.

    Near-duplicates, not just exact ones: the same fact recalled from two sessions
    almost never matches character for character. Same tool and the same
    `default_process` normalisation as the Phase 3 golden set, for the same reason —
    without it, one comma drops a true duplicate below the threshold.

    Duplicate context is worse than useless: it spends budget AND makes a claim look
    corroborated when it was merely stored twice.
    """
    # TODO: keep the first copy of each claim; compare with
    #       `fuzz.token_set_ratio(a, b, processor=default_process)` >= threshold
    #       (both come from `rapidfuzz`; you add the imports).
    #       The processor is not optional — without it one comma drops a true
    #       duplicate below the threshold (the Phase 3 golden set learned this too).
    raise NotImplementedError("dedupe() is yours to implement")


def evict_superseded(lines: Sequence[Line]) -> list[Line]:
    """Remove every line that a later line explicitly replaces.

    A correction has to *delete*, not outrank. Two versions of one fact in the
    window is how a model ends up choosing the stale one.
    """
    # TODO: collect every id named in some line's `supersedes`, then drop those lines.
    raise NotImplementedError("evict_superseded() is yours to implement")


def compress(lines: Sequence[Line], summarize: Summarizer, keep_last: int = 2) -> list[Line]:
    """Fold all but the last `keep_last` lines into one summary line.

    The summary is a lossy WRITE, which is exactly why it carries the ids it came
    from: when the summary turns out to have laundered a guess into a fact, you can
    still say which turns produced it.
    """
    # TODO: nothing to do if there are `keep_last` lines or fewer.
    # TODO: summarize the older lines into ONE line, keep the recent ones verbatim.
    # TODO: the summary's id and source must name the lines it came from — a summary
    #       that cannot be traced back is how a laundered guess becomes a fact.
    raise NotImplementedError("compress() is yours to implement")


def facts_preserved(summary: str, facts: Sequence[str]) -> list[str]:
    """Which hard facts the summarizer dropped. Empty list means it behaved.

    Run this on every summarizer you deploy. Summary drift is invisible in a demo
    and expensive in production.
    """
    return [fact for fact in facts if fact not in summary]


def drop_source(lines: Sequence[Line], source: str) -> list[Line]:
    """Remove everything that came from one source — the poison-removal path."""
    return [line for line in lines if line.source != source]


# ----------------------------------------------------------------- the assembly
def assemble(
    task: str,
    pinned: Sequence[Line],
    candidates: Sequence[Line],
    budget_tokens: int,
    count: Counter = word_counter,
) -> Context:
    """Fill the window under a hard cap. Never exceeds it; never truncates a claim.

    Order matters: the task and pins go in first because they are non-negotiable, so
    if they alone blow the budget you get a `BudgetError` instead of an agent that
    silently lost its own instructions.
    """
    # TODO: refuse a non-positive budget.
    # TODO: task + pinned lines go in FIRST — mark them pinned with
    #       `dataclasses.replace(line, pinned=True)`, which you import — and if
    #       they alone exceed the budget, raise BudgetError with a message that says
    #       what to do about it. Silently dropping your own instructions is worse.
    # TODO: then evict superseded lines, dedupe, and rank by score descending.
    # TODO: fill until the next line would not fit — park it WHOLE and keep going.
    #       Never truncate: half a fact reads as a whole fact to the model.
    # TODO: return a Context carrying tokens, budget and the parked lines.
    raise NotImplementedError("assemble() is yours to implement")


def report(context: Context) -> str:
    """The receipt. Long-run rot shows up here long before it shows up in an answer."""
    filled = 100 * context.tokens / context.budget if context.budget else 0.0
    pins = sum(line.pinned for line in context.lines)
    return (
        f"tokens {context.tokens}/{context.budget} ({filled:.0f}% full)   "
        f"lines {len(context.lines)} (pinned {pins})   parked {len(context.parked)}"
    )


# ------------------------------------------------------------------------ demo
def _demo_lines() -> list[Line]:
    return [
        Line("m1", "Lu works in UTC-5 and prefers meetings after 10:00", "turn-3", score=0.9),
        Line("m2", "Dana is my manager for budget threads", "turn-4", score=0.5),
        Line(
            "m3",
            "Ravi is my manager for budget threads",
            "turn-91",
            score=0.8,
            supersedes=("m2",),
        ),
        Line("m4", "The calendar tool needs an end time or it 400s", "run-12", score=0.7),
        Line("m5", "Lu works in UTC-5, prefers meetings after 10:00", "turn-58", score=0.4),
    ]


def main() -> None:
    pins = [Line("p1", "Never send email without explicit approval", "policy", pinned=True)]
    context = assemble("Draft the Q3 budget note", pins, _demo_lines(), budget_tokens=40)
    print(report(context))
    print(context.render())
    if context.parked:
        print("\nparked (recall on demand):")
        for line in context.parked:
            print(f"  {line.id}  {line.text}")


if __name__ == "__main__":
    main()
