"""TODO: implement the CI merge gate. BOTH must pass to merge:
- quality: faithfulness >= 0.85 AND recall >= 0.80
- safety: zero red-team bypasses

should_merge(report) -> (allowed, reasons_blocked). Reference: ../after/src/gate.py.
"""
from __future__ import annotations

from dataclasses import dataclass

FAITHFULNESS_BAR = 0.85
RECALL_BAR = 0.80


@dataclass
class CIReport:
    faithfulness: float
    recall: float
    redteam_bypasses: int


def should_merge(report: CIReport) -> tuple[bool, list[str]]:
    raise NotImplementedError
