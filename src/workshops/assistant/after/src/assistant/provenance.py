"""Which system produced this number — derived, never typed.

Two consumers, one answer: `core.py` stamps the prompt version onto every
compose span, and `report.py` stamps model/prompt/corpus/dataset onto the report
the merge gate reads. They agree because they call the same functions.

The rule this file exists to enforce: **a version stamp is computed from the
thing it describes.** The alternative — `PROMPT_VERSION = "v3"` next to the
prompt — rots the first time someone edits the prompt in a hurry, and it rots
silently. Nothing fails, no test goes red; the label just stops being true, and
every comparison across that boundary quietly becomes a comparison between two
different systems wearing the same name.

Hashes are truncated to eight hex characters. That is 32 bits — plenty to notice
a change, not enough to be a cryptographic claim, and short enough that a person
can read one out in a review.
"""
from __future__ import annotations

import hashlib
import inspect
import os
import subprocess
from collections.abc import Iterable

STAMP_LENGTH = 8
#: Git's conventional short form. Long enough to be unique in any repo a person
#: will work on, short enough to read out loud during an incident.
SHA_LENGTH = 12


def build_version() -> str:
    """Which commit is serving this request.

    Baked into the image at build time (`ARG GIT_SHA`) and read back from the
    environment, because by then there is no `.git` in the container — and the
    whole point is a stamp the running process can report about ITSELF.

    This is what a post-deploy smoke check compares against
    (`phase8-deploy/03-deploy-observe`). Without it the nastiest deploy failure
    is invisible: a rollout that half-finished, leaving an old machine in the
    pool. It is genuinely healthy, it answers correctly, and every check you
    have passes against it — because it is a working service, just not the one
    you shipped.

    Falls back to the local checkout so a developer's `/health` is honest too,
    and to `dev` outside a repo. It never raises: a version stamp that can take
    down the health endpoint is worse than no version stamp.
    """
    if stamped := os.getenv("GIT_SHA"):
        return stamped[:SHA_LENGTH]
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=2, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return "dev"
    return out.stdout.strip()[:SHA_LENGTH] if out.returncode == 0 else "dev"


def digest(*parts: str) -> str:
    """Content, hashed. Parts are NUL-joined so `["ab", "c"]` and `["a", "bc"]`
    are different inputs — a separator that cannot appear in text is the cheap
    way to avoid a stamp collision that would be very confusing to debug."""
    joined = "\u0000".join(parts).encode()
    return hashlib.sha256(joined).hexdigest()[:STAMP_LENGTH]


def prompt_version() -> str:
    """A stamp for the prompt the composers actually send.

    It hashes the SOURCE of `grounded_prompt`, which means the spans and the
    report both change the moment the prompt does — including the day someone
    changes it without thinking of themselves as changing anything."""
    from assistant import composers

    return f"grounded-{digest(inspect.getsource(composers.grounded_prompt))}"


def corpus_version(docs: Iterable[str]) -> str:
    """A stamp for a set of documents, count included so a human can read it."""
    items = [str(d) for d in docs]
    return f"corpus-{len(items)}-{digest(*items)}"


def dataset_version(label: str, questions: Iterable[str]) -> str:
    """A stamp for an eval set: its name, its size, and its content."""
    items = [str(q) for q in questions]
    return f"{label}-{len(items)}-{digest(*items)}"
