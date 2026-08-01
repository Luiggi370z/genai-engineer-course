"""The interview question bank as a spaced-repetition drill deck.

Load cards, draw today's 5 (weighting cards you've missed), grade yourself,
and let misses resurface sooner. Answer OUT LOUD before flipping.
"""
from __future__ import annotations

import json
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
        rows = [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]
        return cls([Card(**r) for r in rows])

    def draw(self, n: int = 5, rng: random.Random | None = None) -> list[Card]:
        """Weight by misses+1 so fumbled cards resurface more often."""
        rng = rng or random.Random()
        pool = list(self.cards)
        weights = [c.misses + 1 for c in pool]
        picks: list[Card] = []
        for _ in range(min(n, len(pool))):
            c = rng.choices(pool, weights=weights, k=1)[0]
            i = pool.index(c)
            pool.pop(i)
            weights.pop(i)
            picks.append(c)
        return picks

    def grade(self, card_id: str, correct: bool) -> None:
        for c in self.cards:
            if c.id == card_id:
                c.seen += 1
                if not correct:
                    c.misses += 1
                return

    def leech_list(self) -> list[Card]:
        """Cards missed 2+ times — your spaced-repetition priority list."""
        return [c for c in self.cards if c.misses >= 2]
