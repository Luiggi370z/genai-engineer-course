"""A supervisor, two workers, tiered models — and a receipt for both cost AND quality.

The cost delta is the headline, but a crew that is cheaper and worse is not a win, it
is an undeclared quality cut. So every run reports two numbers together, and the
interesting tests are the ones where cheap-and-worse gets caught.

Model calls are simulated from a price table: the routing, the delegation, the cost
arithmetic and the failure handling are exactly what you would ship, while the run
stays offline, free and deterministic. Swap `_invoke` for your Phase-1 client and
nothing else in this file changes.

Three things this lesson is really about:

  * **delegation you can prove.** A supervisor that quietly does the work itself
    passes every output check while defeating the whole design, so the trajectory is
    asserted, not assumed.
  * **quality is per-task, not global.** Each task names the cheapest tier that still
    gets it right; routing below that is a regression you can measure.
  * **a worker failure is data.** One exploding worker degrades the run to `partial`;
    it does not take the other tasks down with it.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

#: USD per million tokens, (input, output). Illustrative tiers, not vendor quotes.
PRICE: dict[str, tuple[float, float]] = {
    "local": (0.0, 0.0),  # your laptop: free, and good enough for triage
    "cheap": (1.0, 5.0),  # Haiku / Flash-Lite class: scoped work
    "frontier": (5.0, 25.0),  # Opus / GPT class: planning and synthesis
}

#: Cheap to expensive. Routing at or above a task's `min_tier` preserves quality.
TIERS: tuple[str, ...] = ("local", "cheap", "frontier")

#: Which worker owns which kind of task. The supervisor owns neither.
SKILLS: dict[str, str] = {"research": "researcher", "write": "writer"}

SUPERVISOR = "supervisor"


@dataclass(frozen=True)
class Task:
    """One unit of delegated work, with the cheapest tier that still does it justice."""

    id: str
    kind: str  # "research" | "write"
    in_tokens: int
    out_tokens: int
    min_tier: str = "local"


@dataclass(frozen=True)
class Call:
    """One model call, attributed to the agent that made it."""

    agent: str
    tier: str
    kind: str
    in_tokens: int
    out_tokens: int
    task_id: str | None = None

    @property
    def cost(self) -> float:
        price_in, price_out = PRICE[self.tier]
        return (self.in_tokens * price_in + self.out_tokens * price_out) / 1_000_000


@dataclass
class CrewRun:
    """Everything that happened, plus the two numbers you report together."""

    calls: list[Call] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)

    @property
    def cost(self) -> float:
        return sum(call.cost for call in self.calls)

    @property
    def status(self) -> str:
        return "partial" if self.errors else "ok"

    @property
    def trace(self) -> list[Call]:
        return list(self.calls)

    def by_agent(self) -> dict[str, float]:
        out: dict[str, float] = {}
        for call in self.calls:
            out[call.agent] = out.get(call.agent, 0.0) + call.cost
        return out


#: A router decides which tier a task runs on. This is the only knob that matters.
Router = Callable[[Task], str]

#: A worker executes one task and returns the call it made. Injected so tests can
#: hand in a worker that explodes, or one that lies about its tier.
Worker = Callable[[Task, str], Call]


def default_route(task: Task) -> str:
    """Cheapest tier that still gets the task right — which is what `min_tier` means.

    Note the direction: triage and scoped work go down the ladder, planning and
    synthesis go up. The popular diagram that routes *with* the expensive model and
    lets cheap models do the work has it backwards for most traffic.
    """
    return task.min_tier


def cheapest_route(_task: Task) -> str:
    """Everything local. Cheapest possible, and the point is that it is worse."""
    return "local"


def frontier_route(_task: Task) -> str:
    """The single-model baseline every cost claim needs to be measured against."""
    return "frontier"


def _invoke(task: Task, tier: str, agent: str) -> Call:
    """Stand-in for a real model call. Replace with your Phase-1 client."""
    return Call(
        agent=agent,
        tier=tier,
        kind=task.kind,
        in_tokens=task.in_tokens,
        out_tokens=task.out_tokens,
        task_id=task.id,
    )


def worker(task: Task, tier: str) -> Call:
    """The honest worker: does its own task, on the tier it was handed."""
    return _invoke(task, tier, agent=SKILLS[task.kind])


def run(
    tasks: Sequence[Task],
    route: Router = default_route,
    workers: dict[str, Worker] | None = None,
    plan_tier: str = "local",
) -> CrewRun:
    """Supervisor plans once, then delegates every task to the worker that owns it.

    The supervisor's own call is on `plan_tier` — cheap by default, because planning a
    handful of known task kinds is not the hard part. Raise it when the *planning* is
    genuinely what is hard: strong orchestrator, cheap workers.
    """
    registry = workers or dict.fromkeys(SKILLS.values(), worker)
    crew = CrewRun()
    plan = Task(id="plan", kind="plan", in_tokens=200 + 20 * len(tasks), out_tokens=100)
    crew.calls.append(_invoke(plan, plan_tier, agent=SUPERVISOR))

    for task in tasks:
        owner = SKILLS.get(task.kind)
        if owner is None or owner not in registry:
            crew.errors[task.id] = f"no worker owns kind={task.kind!r}"
            continue
        try:
            crew.calls.append(registry[owner](task, route(task)))
        except Exception as exc:  # error-as-data: one bad worker is not a dead run
            crew.errors[task.id] = f"{type(exc).__name__}: {exc}"
    return crew


# ----------------------------------------------------------------- the two numbers
def quality(crew: CrewRun, tasks: Sequence[Task]) -> float:
    """Share of tasks answered on a tier good enough for them.

    A stand-in for your Phase 3 eval score, and it behaves the same way: it drops when
    a task is routed below the tier it needed, which is exactly the regression a cost
    optimisation is tempted to hide.
    """
    if not tasks:
        return 1.0
    handled = {call.task_id: call.tier for call in crew.calls if call.task_id}
    good = 0
    for task in tasks:
        tier = handled.get(task.id)
        if tier is not None and TIERS.index(tier) >= TIERS.index(task.min_tier):
            good += 1
    return good / len(tasks)


def delegated(crew: CrewRun) -> bool:
    """Did the supervisor actually hand the work over, or just do it itself?"""
    return not any(call.agent == SUPERVISOR and call.kind in SKILLS for call in crew.calls)


def compare(tasks: Sequence[Task], routes: dict[str, Router]) -> str:
    """The table you put in the PR: cost and quality side by side, never one alone."""
    baseline = run(tasks, route=frontier_route)
    lines = [f"{'route':<12} {'cost':>10} {'vs base':>9} {'quality':>8}  status"]
    for name, router in routes.items():
        crew = run(tasks, route=router)
        delta = 0.0 if baseline.cost == 0 else 1 - crew.cost / baseline.cost
        lines.append(
            f"{name:<12} ${crew.cost:>9.4f} {delta:>8.0%} "
            f"{quality(crew, tasks):>8.0%}  {crew.status}"
        )
    return "\n".join(lines)


def report(crew: CrewRun, tasks: Sequence[Task]) -> str:
    """One run's receipt: total, per-agent split, quality, and any errors."""
    split = "  ".join(f"{agent}=${cost:.4f}" for agent, cost in sorted(crew.by_agent().items()))
    head = (
        f"cost ${crew.cost:.4f}   quality {quality(crew, tasks):.0%}   "
        f"delegated={delegated(crew)}   status={crew.status}"
    )
    body = [head, f"  {split}"]
    for task_id, error in sorted(crew.errors.items()):
        body.append(f"  ! {task_id}: {error}")
    return "\n".join(body)


# ------------------------------------------------------------------------- demo
def _demo_tasks() -> list[Task]:
    return [
        Task("t1", "research", 500, 200, min_tier="local"),
        Task("t2", "research", 600, 250, min_tier="cheap"),
        Task("t3", "research", 500, 200, min_tier="local"),
        Task("t4", "write", 900, 500, min_tier="frontier"),
        Task("t5", "write", 700, 350, min_tier="cheap"),
    ]


def main() -> None:
    tasks = _demo_tasks()
    print(
        compare(
            tasks,
            {
                "frontier": frontier_route,
                "tiered": default_route,
                "all-local": cheapest_route,
            },
        )
    )
    print()
    print(report(run(tasks), tasks))


if __name__ == "__main__":
    main()
