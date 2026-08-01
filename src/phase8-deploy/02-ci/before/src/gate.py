"""The merge-gate logic your CI enforces: quality (eval) AND safety (red-team).

The gates are split on purpose: a quality regression and a safety bypass are
different incidents with different owners, and CI should be able to fail one
without the other. The CLI at the bottom is given — it is what `make eval` and
`make redteam` call — so once the three functions below work, the workflow works.
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
    """TODO 1: return the reasons the QUALITY gate blocks the merge (empty == pass):
    faithfulness below FAITHFULNESS_BAR, recall below RECALL_BAR. Name the number
    and the bar in each reason — a blocked engineer needs to know by how much."""
    raise NotImplementedError


def safety_ok(report: CIReport) -> list[str]:
    """TODO 2: return the reasons the SAFETY gate blocks the merge (empty == pass):
    any red-team bypass at all blocks. There is no acceptable number but zero."""
    raise NotImplementedError


def should_merge(report: CIReport) -> tuple[bool, list[str]]:
    """TODO 3: (allowed, reasons_blocked) — both gates must pass."""
    raise NotImplementedError


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
