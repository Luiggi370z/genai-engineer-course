"""The portfolio page is generated evidence, so the generator itself is on trial.

If `make report` can emit a page that hides a containment breach or invents a
number, the portfolio is worse than none. These tests run the real builder against
the real offline assistant and check the page carries measured content — and that
a breach cannot pass silently.

The JSON half is held to a harder standard than the page, because CI acts on it
without a human in the loop: the stamps must be derived rather than typed, the
numbers must move when the system moves, and a breach must show up as a bypass
count the merge gate can block on.
"""
from __future__ import annotations

import pytest

from assistant.report import (
    REDTEAM_PROBES,
    build_portfolio,
    measure,
    redteam_section,
    versions_for,
)
from assistant.service import build_assistant
from assistant.settings import Settings


@pytest.fixture(scope="module")
def measured():
    return measure()


@pytest.fixture(scope="module")
def page(measured) -> str:
    return measured[0]


def test_build_portfolio_is_still_the_page(page):
    """The old entry point kept working, because the workshop brief names it."""
    assert build_portfolio().startswith("# Portfolio")


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


def test_the_cost_story_is_honest_about_the_offline_tier(page, measured):
    """Zero, arrived at by counting rather than by assertion — the tokens are on
    the page next to the price, so the reader can see WHY it is free."""
    assert measured[1].cost_usd == 0.0
    assert measured[1].tokens_in > 0 and measured[1].tokens_out > 0
    assert "$0.0000" in page
    assert "no per-token invoice" in page


def test_the_json_report_carries_the_four_gated_numbers(measured):
    """These are exactly what phase8-deploy/02-ci budgets. A report that omits
    one is a gate that silently stops checking it."""
    report = measured[1]
    assert 0.0 <= report.faithfulness <= 1.0
    assert 0.0 <= report.recall <= 1.0
    assert report.redteam_bypasses == 0
    assert report.p99_ms >= 0.0
    assert report.cost_usd >= 0.0
    assert report.runs > 0


def test_every_stamp_is_present_and_derived_not_typed(measured):
    """The gate refuses an unstamped report, so an empty stamp would block every
    merge — and a HARD-CODED stamp is worse, because it never blocks anything and
    never tells the truth either."""
    versions = measured[1].versions
    assert set(versions) == {"model", "prompt", "corpus", "dataset"}
    assert all(versions.values())
    assert versions["model"] == "offline-stitcher"  # the tier that actually ran
    assert versions["prompt"].startswith("grounded-")


def test_editing_the_prompt_changes_the_prompt_stamp(monkeypatch):
    """The failure this catches: someone rewrites the prompt, leaves the version
    label alone, and every number recorded before and after gets compared as if
    it came from the same system."""
    assistant = build_assistant(Settings())
    before = versions_for(assistant)["prompt"]

    from assistant import composers

    def rewritten(goal, contexts, state, memories=None):
        return "a different prompt entirely"

    monkeypatch.setattr(composers, "grounded_prompt", rewritten)
    assert versions_for(assistant)["prompt"] != before


def test_the_corpus_and_dataset_stamps_follow_their_inputs(monkeypatch):
    assistant = build_assistant(Settings())
    before = versions_for(assistant)

    from assistant import report

    monkeypatch.setattr(report, "CORPUS", [*report.CORPUS, "a new document"])
    after = versions_for(assistant)
    assert after["corpus"] != before["corpus"]
    assert after["dataset"] == before["dataset"]  # only what changed moves


def test_a_breach_shows_up_as_a_bypass_the_gate_can_block_on():
    """The page says BREACHED; the JSON has to say a NUMBER, because CI does not
    read prose. This is the seam where a hidden breach would become a green
    merge."""
    sabotaged = build_assistant(Settings())
    sabotaged.approvals.consume = lambda *a, **k: "sabotaged-grant"  # type: ignore[method-assign]
    _, report = measure(sabotaged)
    assert report.redteam_bypasses > 0


def test_a_breach_cannot_pass_silently():
    """The safety property of the generator itself: sabotage containment and the
    section must scream, because a portfolio that hides a breach is the exact
    failure the whole course argues against."""
    sabotaged = build_assistant(Settings())
    sabotaged.rag.add(["warmup"])
    # sabotage: hand back a grant for whatever is about to run, so nothing is ever
    # contained. A real store cannot do this — that is the point of the class.
    sabotaged.approvals.consume = lambda *a, **k: "sabotaged-grant"  # type: ignore[method-assign]
    body, contained = redteam_section(sabotaged)
    assert contained is False
    assert "**BREACHED**" in body
