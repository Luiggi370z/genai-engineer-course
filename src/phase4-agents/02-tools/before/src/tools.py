"""TODO: implement three tools to spec.

- read_note(note_id): READ-ONLY. Validate input; return {"text": ...} or {"error": ...}.
- draft_reply(note_id, tone): reversible; returns a draft, never sends.
- delete_note(note_id, approve=False): IRREVERSIBLE — must refuse unless approve=True.

Rules: the docstring says WHAT and WHEN (it's the model's only interface),
type hints are the schema, validate every arg, and return errors as DATA.

Then blank a docstring and watch an agent misuse the tool. Reference: ../after/src/tools.py.
"""
from __future__ import annotations

_NOTES: dict[str, str] = {"1": "buy milk", "2": "call dentist"}


def read_note(note_id: str) -> dict:
    raise NotImplementedError  # TODO 1


def draft_reply(note_id: str, tone: str = "friendly") -> dict:
    raise NotImplementedError  # TODO 2


def delete_note(note_id: str, approve: bool = False) -> dict:
    raise NotImplementedError  # TODO 3
