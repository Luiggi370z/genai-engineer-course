"""TODO: build the layered guardrails.

- decode_and_normalize(text): the text PLUS everything it decodes to.
- squash(text): the text with every separator an attacker can hide behind gone.
- looks_like_injection(text): both scan surfaces, one answer.
- spotlight(untrusted): wrap untrusted content as DATA, not instructions.
- layer1(text): (ok, cleaned/reason) — length cap, block injection, redact PII.
- layer3_output_ok(answer, contexts): no PII leak + grounded in context.

The bar is NOT "zero injections land" — that bar cannot be met. The bar is that
a landed injection cannot fire a gated tool or leak PII, and that is the agent's
job (HITL, least privilege), not this file's. What this file buys is that the
CHEAP obfuscations stop working, so an attacker has to spend real effort to
reach the part of the system that was designed assuming they would.

Attackers work two ways, so the scan has two surfaces:

**Expansion** — "what else does this text say?" Base64, percent-encoding and
HTML entities each let a payload travel as something that does not look like a
payload. Append each decoding rather than substituting it: decoding can add
evidence, and must never quietly rewrite the thing a human will later read.

**Squashing** — "what does this say if you stop respecting the separators?"
`1gn0re`, `i g n o r e`, `Ign<zero-width-space>ore` and `IGNORE` are one word to
a reader and four different strings to a regex.

Reference: ../after/src/guardrails.py.
"""
from __future__ import annotations

import re

PII = [re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")]

# Matched against the EXPANDED text, where ordinary spacing still exists.
INJECTION = [
    re.compile(
        r"ignore\s+(all\s+|the\s+)?(previous|prior|above|earlier).{0,20}instructions?",
        re.I,
    ),
    re.compile(r"you are now|new system prompt|disregard", re.I),
    re.compile(r"reveal.{0,20}(system )?prompt", re.I),
    re.compile(r"forward .* to .*@", re.I),
    # multilingual: attackers do not write English on principle. Same "override
    # the instructions" move in ES/FR/DE/PT — the verb + object pair is the tell.
    re.compile(
        r"(ignora|ignorez|ignoriere|ignore)\b.{0,40}"
        r"(instrucciones|instructions|anweisungen|instru\u00e7\u00f5es)",
        re.I,
    ),
    # exfiltration: moving data OUT is the goal of most landed injections.
    # A transfer verb aimed at an external address or URL is blocked outright.
    re.compile(r"(send|forward|email|upload|export)\b.{0,60}\bto\b.{0,40}@", re.I),
    re.compile(r"(upload|post|send)\b.{0,60}https?://", re.I),
]

# Matched against the SQUASHED text — the same tells, written as if every space,
# punctuation mark and invisible character had been removed, because there they have.
SQUASHED_INJECTION = [
    re.compile(r"ignor[ae](all|the)?(previous|prior|above|earlier)\w{0,12}instruc"),
    re.compile(r"youarenow|newsystemprompt|disregard"),
    re.compile(r"reveal\w{0,12}prompt"),
    re.compile(r"(ignora|ignorez|ignoriere)\w{0,24}(instruc|anweisung)"),
]

# Digits and symbols that stand in for letters, folded on the squashed surface
# only — the reader must still see exactly the text that was sent.
LEET = str.maketrans({
    "0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t",
    "@": "a", "$": "s", "!": "i", "|": "l",
})


def decode_and_normalize(text: str) -> str:
    """TODO 1: the text plus every plaintext hiding inside it.

    Base64 first: find long `[A-Za-z0-9+/]` runs, decode with `validate=True`,
    keep the ones that come back printable. Then the two encodings any payload
    meets on a web path — `urllib.parse.unquote_plus` when the text contains a
    `%`, `html.unescape` when it contains an `&`.

    Append, never substitute. A wrong decoding that ADDS text costs you a false
    positive a human will see; one that REPLACES text loses the evidence."""
    raise NotImplementedError


def squash(text: str) -> str:
    """TODO 2: the text with every separator an attacker can hide behind removed.

    Four steps, in order: NFKC-normalise (fullwidth `ｉｇｎｏｒｅ` folds to
    `ignore`); drop every character whose `unicodedata.category` is `Cf` — that
    is the class of invisible formatting characters, zero-width space and soft
    hyphen among them, whose only role in a payload is to split the word a
    filter is looking for; lowercase and apply LEET; then delete everything that
    is not `[a-z0-9]`.

    `squash("Ign\\u200bore") == squash("1gn0re") == squash("i g n o r e")`."""
    raise NotImplementedError


def looks_like_injection(text: str) -> bool:
    """TODO 3: True if EITHER surface carries a known pattern.

    INJECTION against the expanded text, SQUASHED_INJECTION against the squash
    of that same expanded text — squashing the expansion, not the original, so
    a base64 payload gets both treatments."""
    raise NotImplementedError


def spotlight(untrusted: str) -> str:
    """TODO 4: mark untrusted content as DATA, never instructions."""
    raise NotImplementedError


def layer1(text: str) -> tuple[bool, str]:
    """TODO 5: (ok, cleaned_or_reason).

    Cap the EXPANDED length (a small input that decodes to a megabyte is still a
    megabyte), refuse anything `looks_like_injection` flags with the reason
    `"injection"`, then redact PII from the ORIGINAL text and return it."""
    raise NotImplementedError


def layer3_output_ok(answer: str, contexts: list[str]) -> bool:
    """TODO 6: no PII leak + grounded in context."""
    raise NotImplementedError
