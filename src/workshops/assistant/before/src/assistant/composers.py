"""Answer composition — how evidence becomes prose, in every tier.

Tool planning stays deterministic everywhere (that is policy, and policy should
not depend on model mood); what the model tier changes is COMPOSITION. The
offline composer stitches retrieved context together; the Ollama composers write
grounded prose from the same evidence, batch or streamed. Both consume the same
`grounded_prompt`, and both cite the same `citations_for` ids, so swapping tiers
never changes the shape of an answer.
"""
from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

from assistant import guardrails
from assistant.agent import Step
from assistant.rag import Chunk

ABSTAIN = "I don't know — that isn't in what I can see."

#: (goal, retrieved contexts, tool state, recalled memories) -> answer.
#: Memories are what the assistant already knew about THIS caller; contexts are
#: what it just looked up. They are separate arguments because they are separate
#: kinds of evidence: a citation points at a document, never at a memory.
Composer = Callable[[str, list[str], list[tuple[Step, Any]], list[str]], str]
StreamComposer = Callable[
    [str, list[str], list[tuple[Step, Any]], list[str]], Iterator[str]
]


def citations_for(contexts: list) -> list[dict]:
    """Structured citations for the response: [c1] is contexts[0] and so on. The
    grounded prompt labels evidence with the same ids, so a model-tier answer can
    reference the exact snippet it used.

    A `Chunk` cites itself properly — source document, revision, character span
    and the stable id that can fetch it again — because "source: rag" is not a
    citation, it is the name of the machine that found it. Plain strings still
    work and degrade to exactly that, which is the honest rendering of evidence
    that arrived without provenance."""
    return [
        ctx.cite(f"c{i + 1}")
        if isinstance(ctx, Chunk)
        else {"id": f"c{i + 1}", "source": "rag", "snippet": str(ctx)[:240]}
        for i, ctx in enumerate(contexts)
    ]


def grounded_prompt(
    goal: str,
    contexts: list[str],
    state: list[tuple[Step, Any]],
    memories: list[str] | None = None,
) -> str:
    """One prompt for both the batch and the streaming Ollama composers. Evidence
    is SPOTLIGHTED — wrapped as data the model must not treat as instructions —
    because screened is not the same as trusted.

    Recalled memories are spotlighted too, and for the same reason: the caller
    wrote them, which makes them useful, not trustworthy. They sit in their own
    block so the model can personalise an answer without mistaking a remembered
    preference for a cited source."""
    evidence = [f"[c{i + 1}] {guardrails.spotlight(ctx)}" for i, ctx in enumerate(contexts)]
    evidence += [f"[tool] {guardrails.spotlight(str(out))}" for _, out in state]
    lines = "\n".join(f"- {item}" for item in evidence)
    known = ""
    if memories:
        recalled = "\n".join(f"- {guardrails.spotlight(m)}" for m in memories)
        known = f"\n\nKnown about the person asking:\n{recalled}"
    return (
        "Answer the question using ONLY the evidence below, in one or two "
        "sentences, citing the [c#] ids you used. If the evidence does not "
        f"answer it, reply exactly: {ABSTAIN}\n\n"
        f"Evidence:\n{lines}{known}\n\nQuestion: {goal}"
    )


def offline_compose(
    goal: str,
    contexts: list[str],
    state: list[tuple[Step, Any]],
    memories: list[str] | None = None,
) -> str:
    """TODO 3: the fast-tier composer — build the final answer from retrieved
    context plus any tool outputs in `state`; return ABSTAIN when there is nothing
    to ground an answer in.

    "Nothing to ground in" includes a context that shares no content word
    (len > 3, case-insensitive) with the question: a vector store returns the
    nearest neighbours of ANY query, and when this composer runs as the degraded
    fallback for the model tier, answering an unrelated snippet is fabricated
    grounding — the one failure an abstaining assistant exists to prevent.
    A question with no content words at all cannot be judged; give its contexts
    the benefit of the doubt instead of abstaining reflexively.

    Recalled memories are appended to a grounded answer, never substituted for
    one: knowing the caller's timezone does not answer a question about refunds,
    and a stitcher that dressed a memory up as an answer would abstain less and
    lie more. An answer with nothing but memories behind it is still ABSTAIN."""
    raise NotImplementedError


def model_composer(host: str, model: str) -> Composer:
    """Real-tier composer: grounded generation against local Ollama. Abstention on
    empty evidence stays DETERMINISTIC — a model given nothing to ground on should
    not be asked to improvise a refusal."""

    def compose(
        goal: str,
        contexts: list[str],
        state: list[tuple[Step, Any]],
        memories: list[str] | None = None,
    ) -> str:
        if not contexts and not state:
            return ABSTAIN
        from assistant.adapters import ollama_generate

        return ollama_generate(
            grounded_prompt(goal, contexts, state, memories), host=host, model=model
        )

    return compose


def word_stream(compose: Composer) -> StreamComposer:
    """Adapt any batch composer into a streaming one by yielding word-sized chunks.
    The fast tier streams THROUGH the same SSE path the model tier uses, so the
    endpoint's behavior is testable offline."""

    def stream(
        goal: str,
        contexts: list[str],
        state: list[tuple[Step, Any]],
        memories: list[str] | None = None,
    ) -> Iterator[str]:
        words = compose(goal, contexts, state, memories or []).split(" ")
        for i, word in enumerate(words):
            yield word if i == 0 else " " + word

    return stream


def model_stream_composer(host: str, model: str) -> StreamComposer:
    """Real-tier streaming: tokens leave Ollama and reach the client as they are
    produced, not after the full completion lands."""

    def stream(
        goal: str,
        contexts: list[str],
        state: list[tuple[Step, Any]],
        memories: list[str] | None = None,
    ) -> Iterator[str]:
        if not contexts and not state:
            yield ABSTAIN
            return
        from assistant.adapters import ollama_stream

        yield from ollama_stream(
            grounded_prompt(goal, contexts, state, memories), host=host, model=model
        )

    return stream
