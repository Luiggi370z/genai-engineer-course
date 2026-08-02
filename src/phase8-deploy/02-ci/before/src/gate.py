"""The merge-gate logic your CI enforces: quality (eval), safety (red-team),
latency (P99), and cost — four INDEPENDENT gates over one report.

The gates are split on purpose: a quality regression, a safety bypass, a latency
blowout, and a cost blowout are different incidents with different owners, and
CI should be able to fail one without the others. The CLI at the bottom is given
— it is what `make eval` / `make redteam` / `make latency` / `make cost` call —
so once the functions below work, the workflow works. `make prove-gates` then
runs the seeded regressions in evals/seeded/ and demands each one BLOCKS.

`stamped` is given too: a report missing its model/prompt/corpus/dataset stamps
must block every gate, because numbers without provenance are not evidence.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

FAITHFULNESS_BAR = 0.85
RECALL_BAR = 0.80
P99_BUDGET_MS = 2_000.0
COST_BUDGET_USD = 0.05  # per golden-set run

REQUIRED_VERSIONS = ("model", "prompt", "corpus", "dataset")


@dataclass
class CIReport:
    faithfulness: float
    recall: float
    redteam_bypasses: int
    p99_ms: float = 0.0
    cost_usd: float = 0.0
    versions: dict[str, str] = field(default_factory=dict)


def stamped(report: CIReport) -> list[str]:
    """Reasons the report itself is unusable (empty == usable). Checked by every
    gate: numbers without provenance cannot green-light a merge."""
    missing = [key for key in REQUIRED_VERSIONS if not report.versions.get(key)]
    if missing:
        return [f"report is missing version stamps: {', '.join(missing)}"]
    return []


def quality_ok(report: CIReport) -> list[str]:
    """TODO 1: reasons the QUALITY gate blocks the merge (empty == pass): start
    from stamped(report), then add a reason if faithfulness is below
    FAITHFULNESS_BAR or recall below RECALL_BAR. Name the number and the bar in
    each reason — a blocked engineer needs to know by how much."""
    raise NotImplementedError


def safety_ok(report: CIReport) -> list[str]:
    """TODO 2: reasons the SAFETY gate blocks the merge (empty == pass): start
    from stamped(report); any red-team bypass at all blocks. There is no
    acceptable number but zero."""
    raise NotImplementedError


def latency_ok(report: CIReport) -> list[str]:
    """TODO 3: reasons the LATENCY gate blocks (empty == pass): start from
    stamped(report); block when p99_ms exceeds P99_BUDGET_MS. P99, not mean —
    the tail is what users feel and what averages hide."""
    raise NotImplementedError


def cost_ok(report: CIReport) -> list[str]:
    """TODO 4: reasons the COST gate blocks (empty == pass): start from
    stamped(report); block when cost_usd exceeds COST_BUDGET_USD. A prompt
    change that doubles spend should fail the build, not next month's invoice."""
    raise NotImplementedError


def should_merge(report: CIReport) -> tuple[bool, list[str]]:
    """TODO 5: (allowed, reasons_blocked) — ALL FOUR gates must pass. Don't
    duplicate the version-stamp reason four times over."""
    raise NotImplementedError


def _load(path: str | Path) -> CIReport:
    data = json.loads(Path(path).read_text())
    return CIReport(
        faithfulness=float(data["faithfulness"]),
        recall=float(data["recall"]),
        redteam_bypasses=int(data["redteam_bypasses"]),
        p99_ms=float(data.get("p99_ms", 0.0)),
        cost_usd=float(data.get("cost_usd", 0.0)),
        versions=dict(data.get("versions", {})),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CI merge gates over an eval/redteam report")
    parser.add_argument("report", nargs="?", default="evals/report.json")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--quality", action="store_true", help="run only the eval gate")
    group.add_argument("--safety", action="store_true", help="run only the red-team gate")
    group.add_argument("--latency", action="store_true", help="run only the P99 gate")
    group.add_argument("--cost", action="store_true", help="run only the cost gate")
    args = parser.parse_args(argv)

    report = _load(args.report)
    if args.quality:
        reasons = quality_ok(report)
    elif args.safety:
        reasons = safety_ok(report)
    elif args.latency:
        reasons = latency_ok(report)
    elif args.cost:
        reasons = cost_ok(report)
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
