from dataclasses import replace
from pathlib import Path

from src.gate import (
    COST_BUDGET_USD,
    FAITHFULNESS_BAR,
    P99_BUDGET_MS,
    RECALL_BAR,
    CIReport,
    cost_ok,
    latency_ok,
    main,
    quality_ok,
    safety_ok,
    should_merge,
)

# Fixtures are expressed RELATIVE to the thresholds rather than as literals.
# Written as literals, these tests said "0.7 blocks" and "7800ms blocks", which
# were statements about the bars of the day — recalibrating against a real
# measurement turned four of them red without anything being wrong. What they
# are actually asserting is that a value on the wrong side of a bar blocks, and
# that each gate ignores the others' failures.
#
# The bars' own correctness is a calibration question, and no unit test can
# answer it: see the six-run measurement recorded next to them in `gate.py`.
PASSING = FAITHFULNESS_BAR + (1 - FAITHFULNESS_BAR) / 2
FAILING = FAITHFULNESS_BAR - 0.05
SLOW_MS = P99_BUDGET_MS * 1.5

STAMPS = {
    "model": "qwen3.5:9b",
    "prompt": "grounded-v3",
    "corpus": "handbook-2026-06",
    "dataset": "golden-set-v5",
}


def report(**overrides) -> CIReport:
    base = CIReport(
        faithfulness=PASSING, recall=RECALL_BAR + 0.05, redteam_bypasses=0,
        p99_ms=P99_BUDGET_MS / 2, cost_usd=COST_BUDGET_USD / 2, versions=dict(STAMPS),
    )
    return replace(base, **overrides)


def test_clean_report_merges():
    ok, reasons = should_merge(report())
    assert ok and reasons == []


def test_eval_regression_blocks():
    ok, reasons = should_merge(report(faithfulness=FAILING))
    assert not ok and any("faithfulness" in r for r in reasons)


def test_redteam_bypass_blocks_even_with_good_evals():
    clean_evals = report(faithfulness=PASSING, recall=RECALL_BAR + 0.1, redteam_bypasses=1)
    ok, reasons = should_merge(clean_evals)
    assert not ok and any("bypass" in r for r in reasons)


def test_a_latency_blowout_blocks_on_the_tail():
    ok, reasons = should_merge(report(p99_ms=SLOW_MS))
    assert not ok and any("p99" in r for r in reasons)


def test_a_cost_blowout_blocks_before_the_invoice():
    ok, reasons = should_merge(report(cost_usd=COST_BUDGET_USD * 6))
    assert not ok and any("cost" in r for r in reasons)


def test_an_unstamped_report_blocks_every_gate():
    # "faithfulness 0.91" from an unknown model/prompt/corpus/dataset is not
    # evidence — provenance is a precondition, not a nicety
    naked = report(versions={"model": "qwen3.5:9b"})
    for gate in (quality_ok, safety_ok, latency_ok, cost_ok):
        assert any("version stamps" in r for r in gate(naked)), gate.__name__


def test_the_four_gates_fail_independently():
    # a safety bypass is invisible to the quality gate, a latency blowout to the
    # cost gate, and so on — which is exactly why CI runs them as separate
    # required jobs, not one averaged score.
    failures = {
        quality_ok: report(faithfulness=FAILING),
        safety_ok: report(redteam_bypasses=1),
        latency_ok: report(p99_ms=SLOW_MS),
        cost_ok: report(cost_usd=COST_BUDGET_USD * 20),
    }
    for failing_gate, bad in failures.items():
        for gate in (quality_ok, safety_ok, latency_ok, cost_ok):
            if gate is failing_gate:
                assert gate(bad) != [], gate.__name__
            else:
                blame = f"{gate.__name__} tripped on {failing_gate.__name__}'s failure"
                assert gate(bad) == [], blame


def test_the_cli_passes_on_the_committed_report():
    report_path = str(Path(__file__).resolve().parents[1] / "evals" / "report.json")
    assert main([report_path]) == 0
    for flag in ("--quality", "--safety", "--latency", "--cost"):
        assert main([flag, report_path]) == 0


def test_every_seeded_regression_is_blocked():
    # the prove-gates property: a gate that cannot fail is decoration
    seeded = sorted((Path(__file__).resolve().parents[1] / "evals" / "seeded").glob("*.json"))
    assert len(seeded) >= 6
    for fixture in seeded:
        assert main([str(fixture)]) == 1, f"{fixture.name} should have been blocked"
