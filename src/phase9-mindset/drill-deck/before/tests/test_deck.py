import random

from src.deck import Deck

CARDS = "data/cards.jsonl"


def test_load_and_draw():
    d = Deck.load(CARDS)
    picks = d.draw(3, rng=random.Random(0))
    assert len(picks) == 3
    assert len({c.id for c in picks}) == 3  # no repeats in one draw


def test_grade_tracks_misses():
    d = Deck.load(CARDS)
    d.grade("qb-1", correct=False)
    d.grade("qb-1", correct=False)
    assert any(c.id == "qb-1" and c.misses == 2 for c in d.cards)


def test_leech_list_surfaces_repeat_misses():
    d = Deck.load(CARDS)
    d.grade("qb-5", correct=False)
    d.grade("qb-5", correct=False)
    assert any(c.id == "qb-5" for c in d.leech_list())
