"""Three real tools done right: docstring-as-interface, validation, error-as-data.

- read_note: read-only (no gate).
- draft_reply: reversible write (produces text, doesn't send).
- delete_note: irreversible -> gated by approval the APPLICATION records.

The model picks and fills a tool using ONLY its name, docstring, and type hints.
So the docstring says WHAT it does and WHEN to use it. Validate every argument;
return errors as data so the agent can recover instead of crashing.

One boundary above all: **approval is application state, never a tool argument.**
The model fills every parameter in a tool's signature. Put `approve: bool` in
there and you have handed the model a pen to sign its own permission slip — one
injected instruction and the "gate" approves itself. The human's click lands in
`grant_approval()`, which only application code calls; the tool checks that
record and exposes nothing the model can set to skip it.
"""
from __future__ import annotations

_NOTES: dict[str, str] = {"1": "buy milk", "2": "call dentist"}

# Human approvals on file, keyed by note id. Written by the application when a
# person clicks approve; consumed (one delete per approval) by delete_note.
_APPROVALS: set[str] = set()


def grant_approval(note_id: str) -> None:
    """Record a human's approval to delete one note. Application code only —
    this function is NOT in the tool registry the model sees."""
    _APPROVALS.add(note_id)


def read_note(note_id: str) -> dict:
    """Read a note by id. Use when the user wants to see an existing note.

    Args:
        note_id: the id of the note, e.g. "1".
    Returns {"text": ...} or {"error": ...}.
    """
    if not note_id:
        return {"error": "note_id is required"}
    if note_id not in _NOTES:
        return {"error": f"no note {note_id!r}"}
    return {"text": _NOTES[note_id]}


def draft_reply(note_id: str, tone: str = "friendly") -> dict:
    """Draft (but do NOT send) a reply about a note. Reversible — safe to call.

    Args:
        note_id: which note to reply about.
        tone: "friendly" or "formal".
    """
    note = read_note(note_id)
    if "error" in note:
        return note
    if tone not in {"friendly", "formal"}:
        return {"error": "tone must be 'friendly' or 'formal'"}
    return {"draft": f"[{tone}] Re: {note['text']} — thanks, will do!"}


def delete_note(note_id: str) -> dict:
    """Delete a note permanently. IRREVERSIBLE — a human must approve it first.

    Args:
        note_id: the note to delete.
    Refused unless the application has a human approval on file for this exact
    note. There is no argument that skips the check.
    """
    if note_id not in _APPROVALS:
        return {"error": f"refused: no human approval on file for note {note_id!r}"}
    if note_id not in _NOTES:
        return {"error": f"no note {note_id!r}"}
    _APPROVALS.discard(note_id)  # one approval buys exactly one delete
    del _NOTES[note_id]
    return {"deleted": note_id}
