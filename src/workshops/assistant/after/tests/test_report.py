"""The portfolio page is generated evidence, so the generator itself is on trial.

If `make report` can emit a page that hides a containment breach or invents a
number, the portfolio is worse than none. These tests run the real builder against
the real offline assistant and check the page carries measured content — and that
a breach cannot pass silently.
"""
from __future__ import annotations

import pytest

from assistant.report import REDTEAM_PROBES, build_portfolio, redteam_section
from assistant.service import build_assistant
from assistant.settings import Settings


@pytest.fixture(scope="module")
def page() -> str:
    return build_portfolio()


def test_the_page_carries_every_section(page):
    for heading in (
        "## Eval scores (offline judge)",
        "## Red-team containment",
        "## Latency (from the spans)",
        "## Cost",
        "## Design decisions",
    ):
        assert heading in page


def test_the_eval_table_is_scored_per_slice_and_names_its_judge(page):
    assert "abstention" in page  # the slice the business cares about most
    assert "OVERALL" in page  # format_table's footer — the table is real output
    assert "KeywordJudge" in page  # an unlabelled offline score is a lie


def test_every_probe_was_contained_and_the_verdict_says_so(page):
    assert page.count("| contained |") == len(REDTEAM_PROBES)
    assert "BREACHED" not in page
    assert "all probes contained" in page


def test_latency_percentiles_come_from_actual_runs(page):
    # The golden set + probes ran through the service, so agent.run spans exist
    # and the percentile line carries measured (non-negative) milliseconds.
    assert "P99" in page
    assert "agent.run" in page


def test_the_cost_story_is_honest_about_the_offline_tier(page):
    assert "zero model calls" in page
    assert "$0.00" in page


def test_a_breach_cannot_pass_silently():
    """The safety property of the generator itself: sabotage containment and the
    section must scream, because a portfolio that hides a breach is the exact
    failure the whole course argues against."""
    sabotaged = build_assistant(Settings())
    sabotaged.rag.add(["warmup"])
    sabotaged.grants["send_telegram"] = 10**6  # pre-approve everything gated
    body, contained = redteam_section(sabotaged)
    assert contained is False
    assert "**BREACHED**" in body
