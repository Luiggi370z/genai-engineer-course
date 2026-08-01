from pathlib import Path

from src.gate import CIReport, main, quality_ok, safety_ok, should_merge


def test_clean_report_merges():
    ok, reasons = should_merge(CIReport(faithfulness=0.9, recall=0.85, redteam_bypasses=0))
    assert ok and reasons == []


def test_eval_regression_blocks():
    ok, reasons = should_merge(CIReport(faithfulness=0.7, recall=0.85, redteam_bypasses=0))
    assert not ok and any("faithfulness" in r for r in reasons)


def test_redteam_bypass_blocks_even_with_good_evals():
    ok, reasons = should_merge(CIReport(faithfulness=0.95, recall=0.9, redteam_bypasses=1))
    assert not ok and any("bypass" in r for r in reasons)


def test_the_two_gates_fail_independently():
    # a safety bypass is invisible to the quality gate, and vice versa — which is
    # exactly why CI runs them as two required jobs, not one averaged score.
    bypass_only = CIReport(faithfulness=0.95, recall=0.9, redteam_bypasses=1)
    assert quality_ok(bypass_only) == []
    assert safety_ok(bypass_only) != []

    regression_only = CIReport(faithfulness=0.7, recall=0.9, redteam_bypasses=0)
    assert safety_ok(regression_only) == []
    assert quality_ok(regression_only) != []


def test_the_cli_passes_on_the_committed_report():
    report = str(Path(__file__).resolve().parents[1] / "evals" / "report.json")
    assert main([report]) == 0
    assert main(["--quality", report]) == 0
    assert main(["--safety", report]) == 0
