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


class StreamTruncated(Exception):
    """Raised by a `StreamComposer` that stopped partway through an answer.

    Part of the streaming contract rather than an error to swallow: chunks are
    already on the wire, so the stream cannot restart, but the fragment left
    behind is not the answer either. A model that dies mid-sentence tends to
    leave something grammatical, and grammatical reads as complete — which is
    how a truncation gets filed as a bad answer instead of a failed request.
    `output_gate` turns this into an explicit `truncated` terminal event.
    """


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


def memory_prompt(goal: str, memories: list[str]) -> str:
    """The prompt for an answer whose only evidence is what the caller said.

    Deliberately not `grounded_prompt` with the documents left out. That prompt
    demands `[c#]` citations, and a model asked to cite when there is nothing to
    cite invents an id — which is how a remembered preference gets served
    wearing a document's authority. This one has no citation slot to fill and
    asks for the attribution that is actually true: they told us.
    """
    recalled = "\n".join(f"- {guardrails.spotlight(m)}" for m in memories)
    return (
        "Answer the question using ONLY what this person told you earlier, "
        "below, in one sentence. Say that they told you. Do NOT cite sources or "
        "use [c#] markers — there are no documents here. If what they told you "
        f"does not answer the question, reply exactly: {ABSTAIN}\n\n"
        f"What they told you earlier:\n{recalled}\n\nQuestion: {goal}"
    )


def _shares_a_content_word(goal: str, context: str) -> bool:
    """Lexical overlap on words long enough to mean something. A goal with no
    content words at all cannot be judged, so its contexts get the benefit of
    the doubt rather than a reflexive abstention."""
    words = {w for w in goal.lower().split() if len(w) > 3}
    if not words:
        return True
    lowered = context.lower()
    return any(w in lowered for w in words)


def relevant_contexts(goal: str, contexts: list | None) -> list:
    """The retrieved contexts that could plausibly answer THIS question.

    The same filter as `relevant_memories`, and it has to be applied in the same
    places, because "we retrieved something" and "we retrieved an answer" are
    different facts. BM25 conflates them harmlessly — no overlap, no hit — but a
    vector store returns the nearest neighbours of any question, so with Qdrant
    behind it `contexts` is never empty. The deployed stack answered a timezone
    question with "I don't know [c1][c2]" while the caller's own timezone sat two
    fields away in the same response: the documents were present, irrelevant, and
    still counted as the evidence class, which sent the question to the prompt
    that demands citations instead of the one that can use a memory.
    """
    return [ctx for ctx in contexts or [] if _shares_a_content_word(goal, str(ctx))]


def relevant_memories(goal: str, memories: list[str] | None) -> list[str]:
    """The memories that could plausibly answer THIS question.

    The filter is what keeps memory from becoming a licence to answer anything.
    Recall is cheap and greedy — it returns what it has about the caller — so
    without a relevance check, knowing someone's timezone would turn every
    unanswerable question about the refund policy into an answer about Lima.
    """
    return [m for m in memories or [] if _shares_a_content_word(goal, m)]


def grounding_of(
    contexts: list[str],
    state: list[tuple[Step, Any]],
    memories: list[str] | None,
    goal: str = "",
) -> str:
    """Which class of evidence an answer stands on: documents, tools, memory, or
    nothing.

    Worth reporting because the three are not interchangeable to a reader. A
    document-grounded answer is checkable against a citation; a memory-grounded
    one is only as good as what the caller said about themselves, and has no
    citation by design (ADR-0008). Collapsing them leaves the caller unable to
    tell "the handbook says" from "you said".

    Relevance, not presence. `if contexts:` was true of every request the moment
    the store became a vector index, which made "documents" the answer to a
    question nobody had asked and made the memory class unreachable in the
    deployed stack while passing every offline test.
    """
    if relevant_contexts(goal, contexts):
        return "documents"
    if state:
        return "tools"
    if relevant_memories(goal, memories):
        return "memory"
    return "none"


def offline_compose(
    goal: str,
    contexts: list[str],
    state: list[tuple[Step, Any]],
    memories: list[str] | None = None,
) -> str:
    """Fast-tier composer: deterministic, offline, honest about its limits.

    A context is only an ANSWER if it shares a content word with the question.
    The BM25 tier makes that filter invisible (no overlap, no retrieval), but a
    vector store returns the nearest neighbours of anything — and when this
    composer runs as the degraded fallback for the model tier, "nearest" is not
    "relevant". Answering an unrelated snippet would be a fabricated grounding,
    which is the one failure an abstaining assistant exists to prevent.

    Recalled memories decorate a document answer and never replace one: knowing
    the caller's timezone does not answer a question about refunds. But when
    memory is the ONLY evidence and it does bear on the question, it answers —
    attributed, uncited. Abstaining there was the older, worse bug: "Lima" sat
    in the response metadata while the answer said it did not know."""
    fetched = [str(out) for _, out in state]
    grounded = relevant_contexts(goal, contexts)
    if grounded:
        answer = grounded[0]
        if fetched:
            answer += " (" + "; ".join(fetched) + ")"
        return _with_memories(answer, memories)
    if fetched:
        return _with_memories(" ".join(fetched), memories)
    recalled = relevant_memories(goal, memories)
    if recalled:
        # Phrased as attribution, not as fact. The assistant did not look this
        # up and must not sound like it did.
        return "You told me earlier: " + "; ".join(recalled) + "."
    return ABSTAIN


def _with_memories(answer: str, memories: list[str] | None) -> str:
    if not memories:
        return answer
    return answer + " [recalled: " + "; ".join(memories) + "]"


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
        recalled = relevant_memories(goal, memories)
        grounded = relevant_contexts(goal, contexts)
        if not grounded and not state and not recalled:
            return ABSTAIN
        from assistant.adapters import ollama_generate

        # Memory-only questions get their own prompt, because the grounded one
        # asks for [c#] citations and there is nothing here to number.
        #
        # Keyed on RELEVANT contexts rather than on any: a vector store hands
        # back three neighbours for "which timezone should we schedule in", and
        # the grounded prompt then instructs the model to answer from those and
        # cite them — so it abstains, correctly, on evidence that was never the
        # evidence. The memory it needed was in the prompt the whole time, in a
        # block the instructions did not permit it to use.
        prompt = (
            memory_prompt(goal, recalled)
            if not grounded and not state
            else grounded_prompt(goal, contexts, state, memories)
        )
        return ollama_generate(prompt, host=host, model=model)

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
        recalled = relevant_memories(goal, memories)
        grounded = relevant_contexts(goal, contexts)
        if not grounded and not state and not recalled:
            yield ABSTAIN
            return
        from assistant.adapters import ollama_stream

        # Same choice as the batch composer, on the same terms. Streaming and
        # batch answering the same question differently is a bug a client sees
        # and nobody can explain.
        prompt = (
            memory_prompt(goal, recalled)
            if not grounded and not state
            else grounded_prompt(goal, contexts, state, memories)
        )
        yield from ollama_stream(prompt, host=host, model=model)

    return stream
