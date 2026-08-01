"""Offline, deterministic tests for the crew: cost, quality, delegation, failure."""

from __future__ import annotations

import pytest

from src.crew import (
    SKILLS,
    SUPERVISOR,
    Call,
    Task,
    cheapest_route,
    compare,
    default_route,
    delegated,
    frontier_route,
    quality,
    report,
    run,
    worker,
)

TASKS = [
    Task("t1", "research", 500, 200, min_tier="local"),
    Task("t2", "research", 600, 250, min_tier="cheap"),
    Task("t3", "research", 500, 200, min_tier="local"),
    Task("t4", "write", 900, 500, min_tier="frontier"),
    Task("t5", "write", 700, 350, min_tier="cheap"),
]


def test_tiering_is_cheaper_than_the_single_model_baseline() -> None:
    tiered = run(TASKS)
    baseline = run(TASKS, route=frontier_route)
    assert tiered.cost < baseline.cost


def test_tiering_keeps_quality_while_it_saves() -> None:
    """The claim that makes a cost number worth quoting."""
    tiered = run(TASKS)
    baseline = run(TASKS, route=frontier_route)
    assert quality(tiered, TASKS) == quality(baseline, TASKS) == 1.0


def test_the_cheapest_route_is_an_undeclared_quality_cut() -> None:
    """Cheaper AND worse is not a win — this is the test that says so out loud."""
    penny_pinching = run(TASKS, route=cheapest_route)
    assert penny_pinching.cost == 0.0
    assert quality(penny_pinching, TASKS) < 1.0


def test_easy_work_lands_on_the_free_tier() -> None:
    crew = run([TASKS[0]])
    worker_calls = [call for call in crew.calls if call.agent != SUPERVISOR]
    assert [call.tier for call in worker_calls] == ["local"]
    assert sum(call.cost for call in worker_calls) == 0.0


def test_the_supervisor_actually_delegates() -> None:
    """A supervisor doing the work itself passes every output check and wastes the design."""
    crew = run(TASKS)
    assert delegated(crew)
    assert {call.agent for call in crew.calls} == {SUPERVISOR, *SKILLS.values()}


def test_a_supervisor_that_does_the_work_itself_is_caught() -> None:
    def hoarding_worker(task: Task, tier: str) -> Call:
        return Call(SUPERVISOR, tier, task.kind, task.in_tokens, task.out_tokens, task.id)

    crew = run(TASKS, workers=dict.fromkeys(SKILLS.values(), hoarding_worker))
    assert not delegated(crew)


def test_each_kind_of_work_goes_to_the_worker_that_owns_it() -> None:
    crew = run(TASKS)
    owners = {(call.kind, call.agent) for call in crew.calls if call.task_id != "plan"}
    assert owners == {("research", "researcher"), ("write", "writer")}


def test_one_exploding_worker_does_not_sink_the_run() -> None:
    def exploding(task: Task, tier: str) -> Call:
        raise TimeoutError("search backend took too long")

    crew = run(TASKS, workers={"researcher": exploding, "writer": worker})
    assert crew.status == "partial"
    assert set(crew.errors) == {"t1", "t2", "t3"}
    assert [call.task_id for call in crew.calls if call.agent == "writer"] == ["t4", "t5"]


def test_a_task_nobody_owns_is_an_error_not_a_crash() -> None:
    crew = run([Task("x1", "translate", 100, 100)])
    assert crew.status == "partial"
    assert "no worker owns" in crew.errors["x1"]


def test_the_supervisor_plans_once_regardless_of_task_count() -> None:
    assert sum(call.agent == SUPERVISOR for call in run(TASKS).calls) == 1
    assert sum(call.agent == SUPERVISOR for call in run(TASKS[:2]).calls) == 1


def test_cost_is_attributed_per_agent() -> None:
    split = run(TASKS).by_agent()
    assert set(split) == {SUPERVISOR, "researcher", "writer"}
    assert split[SUPERVISOR] == 0.0  # planning on the free tier
    assert sum(split.values()) == pytest.approx(run(TASKS).cost)


def test_the_comparison_table_reports_cost_and_quality_together() -> None:
    table = compare(TASKS, {"tiered": default_route, "all-local": cheapest_route})
    assert "quality" in table and "$" in table
    assert table.count("\n") == 2  # header + one row per route


def test_the_report_names_the_failure() -> None:
    crew = run([Task("x1", "translate", 100, 100)])
    assert "! x1" in report(crew, [Task("x1", "translate", 100, 100)])
