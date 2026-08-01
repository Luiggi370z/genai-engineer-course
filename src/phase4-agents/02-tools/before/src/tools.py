"""TODO: implement three tools to spec.

- read_note(note_id): READ-ONLY. Validate input; return {"text": ...} or {"error": ...}.
- draft_reply(note_id, tone): reversible; returns a draft, never sends.
- delete_note(note_id): IRREVERSIBLE — refuse unless the application has recorded
  a human approval for that note (see grant_approval below).

Rules: the docstring says WHAT and WHEN (it's the model's only interface),
type hints are the schema, validate every arg, and return errors as DATA.

The one rule you cannot bend: approval is APPLICATION state, never a tool
argument. The model fills every parameter in a tool signature — an
`approve: bool` parameter is a gate the model can open itself.

Then blank a docstring and watch an agent misuse the tool. Reference: ../after/src/tools.py.
"""
from __future__ import annotations

_NOTES: dict[str, str] = {"1": "buy milk", "2": "call dentist"}

# Human approvals on file, keyed by note id. The application writes here when a
# person clicks approve; the model never sees this set or the granting function.
_APPROVALS: set[str] = set()


def grant_approval(note_id: str) -> None:
    """Record a human's approval to delete one note. Application code only —
    this function is NOT in the tool registry the model sees."""
    _APPROVALS.add(note_id)


def read_note(note_id: str) -> dict:
    raise NotImplementedError  # TODO 1


def draft_reply(note_id: str, tone: str = "friendly") -> dict:
    raise NotImplementedError  # TODO 2


def delete_note(note_id: str) -> dict:
    raise NotImplementedError  # TODO 3: check _APPROVALS, consume on success
