"""TODO: which system produced this number — derived, never typed.

Two consumers, one answer: `core.py` stamps the prompt version onto every
compose span, and `report.py` stamps model/prompt/corpus/dataset onto the report
the merge gate reads. They agree because they call the same functions.

The rule this file exists to enforce: **a version stamp is computed from the
thing it describes.** The alternative — `PROMPT_VERSION = "v3"` next to the
prompt — rots the first time someone edits the prompt in a hurry, and it rots
silently. Nothing fails, no test goes red; the label just stops being true, and
every comparison across that boundary quietly becomes a comparison between two
different systems wearing the same name.

Reference: ../../after/src/assistant/provenance.py.
"""
from __future__ import annotations

from collections.abc import Iterable

STAMP_LENGTH = 8
#: Git's conventional short form.
SHA_LENGTH = 12


def build_version() -> str:
    """TODO 1: which commit is serving this request.

    Read `GIT_SHA` from the environment (the Dockerfile bakes it in at build
    time — by then there is no `.git` in the container, and the whole point is a
    stamp the running process can report about ITSELF). Fall back to
    `git rev-parse HEAD` for a local checkout, then to `"dev"`.

    `/health` reports it and a post-deploy smoke check compares it to the SHA it
    just shipped. Without it the nastiest deploy failure is invisible: a rollout
    that half-finished, leaving an old machine in the pool. It is healthy, it
    answers correctly, and every other check passes against it.

    Never raise. A version stamp that can take down the health endpoint is worse
    than no version stamp — wrap the subprocess call and return `"dev"`.
    """
    raise NotImplementedError


def digest(*parts: str) -> str:
    """TODO 2: eight hex characters of sha256 over the parts.

    Join with a separator that cannot appear in the text (`"\\u0000"`) before
    hashing, so `["ab", "c"]` and `["a", "bc"]` are different inputs. Truncate to
    STAMP_LENGTH: 32 bits is plenty to notice a change, not a cryptographic
    claim, and short enough to read out in a review.
    """
    raise NotImplementedError


def prompt_version() -> str:
    """TODO 3: a stamp for the prompt the composers actually send.

    Hash `inspect.getsource(composers.grounded_prompt)` and return
    `f"grounded-{...}"`. Hashing the SOURCE is the point: the spans and the
    report both change the moment the prompt does — including the day someone
    changes it without thinking of themselves as changing anything.

    Import composers inside the function; core.py imports this module, and a
    module-level import would close the circle.
    """
    raise NotImplementedError


def corpus_version(docs: Iterable[str]) -> str:
    """TODO 4: a stamp for a set of documents — `corpus-<count>-<digest>`, with
    the count included so a human can read it."""
    raise NotImplementedError


def dataset_version(label: str, questions: Iterable[str]) -> str:
    """TODO 5: a stamp for an eval set: `<label>-<count>-<digest>`."""
    raise NotImplementedError
