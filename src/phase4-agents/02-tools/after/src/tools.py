"""Three real tools done right: docstring-as-interface, validation, error-as-data.

- read_note: read-only (no gate).
- draft_reply: reversible write (produces text, doesn't send).
- delete_note: irreversible -> must be gated (requires approve=True).

The model picks and fills a tool using ONLY its name, docstring, and type hints.
So the docstring says WHAT it does and WHEN to use it. Validate every argument;
return errors as data so the agent can recover instead of crashing.
"""
from __future__ import annotations

_NOTES: dict[str, str] = {"1": "buy milk", "2": "call dentist"}


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


def delete_note(note_id: str, approve: bool = False) -> dict:
    """Delete a note permanently. IRREVERSIBLE — requires human approval.

    Args:
        note_id: the note to delete.
        approve: must be True (a human approved) or the delete is refused.
    """
    if not approve:
        return {"error": "refused: delete requires human approval (approve=True)"}
    if note_id not in _NOTES:
        return {"error": f"no note {note_id!r}"}
    del _NOTES[note_id]
    return {"deleted": note_id}
