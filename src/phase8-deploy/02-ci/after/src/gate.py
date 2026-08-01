"""The merge-gate logic your CI enforces: quality (eval) AND safety (red-team).

Kept as a pure function so you can unit-test the policy itself.
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
    """Return (allowed, reasons_blocked). Both gates must pass."""
    reasons: list[str] = []
    if report.faithfulness < FAITHFULNESS_BAR:
        reasons.append(f"faithfulness {report.faithfulness} < {FAITHFULNESS_BAR}")
    if report.recall < RECALL_BAR:
        reasons.append(f"recall {report.recall} < {RECALL_BAR}")
    if report.redteam_bypasses > 0:
        reasons.append(f"{report.redteam_bypasses} red-team bypass(es)")
    return (len(reasons) == 0, reasons)
