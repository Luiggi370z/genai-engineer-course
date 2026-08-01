"""The merge-gate logic your CI enforces: quality (eval) AND safety (red-team).

Kept as pure functions so the policy is unit-testable, and exposed as a CLI so the
`make eval` / `make redteam` targets a workflow calls actually run something. The two
gates are split on purpose: a quality regression and a safety bypass are different
incidents with different owners, and CI should be able to fail one without the other.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

FAITHFULNESS_BAR = 0.85
RECALL_BAR = 0.80


@dataclass
class CIReport:
    faithfulness: float
    recall: float
    redteam_bypasses: int


def quality_ok(report: CIReport) -> list[str]:
    """Reasons the quality gate blocks the merge (empty == pass)."""
    reasons: list[str] = []
    if report.faithfulness < FAITHFULNESS_BAR:
        reasons.append(f"faithfulness {report.faithfulness} < {FAITHFULNESS_BAR}")
    if report.recall < RECALL_BAR:
        reasons.append(f"recall {report.recall} < {RECALL_BAR}")
    return reasons


def safety_ok(report: CIReport) -> list[str]:
    """Reasons the safety gate blocks the merge (empty == pass)."""
    if report.redteam_bypasses > 0:
        return [f"{report.redteam_bypasses} red-team bypass(es)"]
    return []


def should_merge(report: CIReport) -> tuple[bool, list[str]]:
    """Return (allowed, reasons_blocked). Both gates must pass."""
    reasons = quality_ok(report) + safety_ok(report)
    return (len(reasons) == 0, reasons)


def _load(path: str | Path) -> CIReport:
    data = json.loads(Path(path).read_text())
    return CIReport(
        faithfulness=float(data["faithfulness"]),
        recall=float(data["recall"]),
        redteam_bypasses=int(data["redteam_bypasses"]),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CI merge gate over an eval/redteam report")
    parser.add_argument("report", nargs="?", default="evals/report.json")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--quality", action="store_true", help="run only the eval gate")
    group.add_argument("--safety", action="store_true", help="run only the red-team gate")
    args = parser.parse_args(argv)

    report = _load(args.report)
    if args.quality:
        reasons = quality_ok(report)
    elif args.safety:
        reasons = safety_ok(report)
    else:
        _, reasons = should_merge(report)

    if reasons:
        print("BLOCKED:")
        for reason in reasons:
            print(f"  - {reason}")
        return 1
    print("OK: gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
