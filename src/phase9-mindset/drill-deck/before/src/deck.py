"""TODO: build a spaced-repetition drill deck from the question bank.

- Deck.load(path): read cards.jsonl.
- draw(n): pick n cards, weighting by misses+1 so fumbled ones resurface.
- grade(card_id, correct): bump seen; bump misses on a miss.
- leech_list(): cards missed 2+ times (your priority list).

Answer OUT LOUD before flipping. Reference: ../after/src/deck.py.
"""
from __future__ import annotations

import json  # noqa: F401 — you will need this for TODO 1
import random
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Card:
    id: str
    q: str
    a: str
    misses: int = 0
    seen: int = 0


@dataclass
class Deck:
    cards: list[Card] = field(default_factory=list)

    @classmethod
    def load(cls, path: str | Path) -> Deck:
        raise NotImplementedError  # TODO 1

    def draw(self, n: int = 5, rng: random.Random | None = None) -> list[Card]:
        raise NotImplementedError  # TODO 2

    def grade(self, card_id: str, correct: bool) -> None:
        raise NotImplementedError  # TODO 3

    def leech_list(self) -> list[Card]:
        raise NotImplementedError  # TODO 4
