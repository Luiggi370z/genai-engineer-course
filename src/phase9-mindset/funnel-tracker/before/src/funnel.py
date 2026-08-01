"""TODO: instrument the job search and find the leaking stage.

- Funnel.rates(): conversion at each of the 4 stages.
- leaking_stage(): the stage furthest below its floor (proportionally); ignore
  stages whose INPUT volume is <5 (too small to trust). Return None if healthy.
- prescription(): the one fix to apply for that stage.

Rejection is a metric, not a verdict. Reference: ../after/src/funnel.py.
"""
from __future__ import annotations

from dataclasses import dataclass

HEALTHY = {
    "applications->screens": 0.10,
    "screens->technicals": 0.50,
    "technicals->onsites": 0.50,
    "onsites->offers": 0.30,
}
FIX = {
    "applications->screens": "resume + targeting (lead every bullet with a metric)",
    "screens->technicals": "your story + fundamentals (drill deck)",
    "technicals->onsites": "mock the design round; practice out loud",
    "onsites->offers": "behavioral prep + closing the design round",
}


@dataclass
class Funnel:
    applications: int
    screens: int
    technicals: int
    onsites: int
    offers: int

    def rates(self) -> dict[str, float]:
        raise NotImplementedError  # TODO 1

    def leaking_stage(self) -> str | None:
        raise NotImplementedError  # TODO 2

    def prescription(self) -> str:
        raise NotImplementedError  # TODO 3
