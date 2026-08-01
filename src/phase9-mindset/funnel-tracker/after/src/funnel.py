"""Instrument your job search like a pipeline and find the failing stage.

Track four stages; compute conversion at each; flag the one that leaks worst
against healthy benchmarks. Debug the stage that's actually failing.
"""
from __future__ import annotations

from dataclasses import dataclass

# rough healthy conversion floors per stage (directional, not gospel)
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
        def r(n: int, d: int) -> float:
            return 0.0 if d == 0 else n / d
        return {
            "applications->screens": r(self.screens, self.applications),
            "screens->technicals": r(self.technicals, self.screens),
            "technicals->onsites": r(self.onsites, self.technicals),
            "onsites->offers": r(self.offers, self.onsites),
        }

    def leaking_stage(self) -> str | None:
        """The stage furthest below its healthy floor, proportionally. Fix it first."""
        rates = self.rates()
        # a stage needs enough volume at its INPUT to be measurable (n>=5),
        # so a single unlucky onsite doesn't masquerade as the worst leak.
        denom = {
            "applications->screens": self.applications,
            "screens->technicals": self.screens,
            "technicals->onsites": self.technicals,
            "onsites->offers": self.onsites,
        }
        shortfall = {
            k: (HEALTHY[k] - v) / HEALTHY[k]
            for k, v in rates.items()
            if denom[k] >= 5
        }
        if not shortfall:
            return None
        worst = max(shortfall, key=lambda k: shortfall[k])
        return worst if shortfall[worst] > 0 else None

    def prescription(self) -> str:
        stage = self.leaking_stage()
        return "Funnel healthy — keep applying." if stage is None else f"Fix {stage}: {FIX[stage]}"
