"""The merge-gate logic your CI enforces: quality (eval), safety (red-team),
latency (P99), and cost — four INDEPENDENT gates over one report.

Kept as pure functions so the policy is unit-testable, and exposed as a CLI so the
`make eval` / `make redteam` / `make latency` / `make cost` targets a workflow
calls actually run something. The gates are split on purpose: a quality
regression, a safety bypass, a latency blowout, and a cost blowout are different
incidents with different owners, and CI should be able to fail one without the
others.

The report also carries VERSION metadata (model/prompt/corpus/dataset). An
unversioned report is unreviewable — "faithfulness 0.91" means nothing if you
cannot say which model, which prompt, and which golden set produced it — so a
report missing its stamps blocks every gate.
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
    """Reasons the quality gate blocks the merge (empty == pass)."""
    reasons = stamped(report)
    if report.faithfulness < FAITHFULNESS_BAR:
        reasons.append(f"faithfulness {report.faithfulness} < {FAITHFULNESS_BAR}")
    if report.recall < RECALL_BAR:
        reasons.append(f"recall {report.recall} < {RECALL_BAR}")
    return reasons


def safety_ok(report: CIReport) -> list[str]:
    """Reasons the safety gate blocks the merge (empty == pass)."""
    reasons = stamped(report)
    if report.redteam_bypasses > 0:
        reasons.append(f"{report.redteam_bypasses} red-team bypass(es)")
    return reasons


def latency_ok(report: CIReport) -> list[str]:
    """Reasons the latency gate blocks (empty == pass). P99, not mean: the tail
    is what users feel and what averages hide."""
    reasons = stamped(report)
    if report.p99_ms > P99_BUDGET_MS:
        reasons.append(f"p99 {report.p99_ms}ms > {P99_BUDGET_MS}ms budget")
    return reasons


def cost_ok(report: CIReport) -> list[str]:
    """Reasons the cost gate blocks (empty == pass). A prompt change that doubles
    spend should fail the build, not surface on next month's invoice."""
    reasons = stamped(report)
    if report.cost_usd > COST_BUDGET_USD:
        reasons.append(f"cost ${report.cost_usd} > ${COST_BUDGET_USD} budget")
    return reasons


def should_merge(report: CIReport) -> tuple[bool, list[str]]:
    """Return (allowed, reasons_blocked). All four gates must pass."""
    reasons = stamped(report)
    for gate in (quality_ok, safety_ok, latency_ok, cost_ok):
        reasons.extend(r for r in gate(report) if r not in reasons)
    return (len(reasons) == 0, reasons)


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
