from src.gate import CIReport, should_merge


def test_clean_report_merges():
    ok, reasons = should_merge(CIReport(faithfulness=0.9, recall=0.85, redteam_bypasses=0))
    assert ok and reasons == []


def test_eval_regression_blocks():
    ok, reasons = should_merge(CIReport(faithfulness=0.7, recall=0.85, redteam_bypasses=0))
    assert not ok and any("faithfulness" in r for r in reasons)


def test_redteam_bypass_blocks_even_with_good_evals():
    ok, reasons = should_merge(CIReport(faithfulness=0.95, recall=0.9, redteam_bypasses=1))
    assert not ok and any("bypass" in r for r in reasons)
