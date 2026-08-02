"""Workshop 8 layer — OpenTelemetry around the agent loop and every tool.

An agent is harder to observe than a single model call, because the interesting
question is never "how long did that take". It is *what did it do* — which tools,
in what order, how many steps, and where the eight seconds actually went. A single
timer on `run()` cannot answer any of that; a span tree can.

Two design choices worth copying:

**Tools are instrumented by wrapping the registry, not by editing tools.** No tool
knows it is being traced, which means adding a tool cannot forget to. Cross-cutting
concerns belong at the seam, not sprinkled through every implementation.

**The vendor is an environment variable.** These are plain OTel spans — using
OpenInference names where a convention exists and clearly-marked custom names
where none does — so Langfuse, Phoenix or your existing APM all read them. The
in-memory exporter used in tests is the same code path as production.
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import Status, StatusCode, Tracer

from assistant.tools import Tool

# tool.name follows OpenInference's tool-span convention. The rest are OUR
# extensions — no convention covers agent step counts or approval pauses (yet),
# so they are labelled custom rather than passed off as standard. Where an
# agreed name exists, use it: a dashboard that has never seen this repo can
# still read the trace.
TOOL_NAME = "tool.name"
TOOL_GATED = "tool.requires_approval"
AGENT_STEPS = "agent.step_count"
AGENT_PAUSED = "agent.paused_for_approval"
AGENT_OUTCOME = "agent.outcome"  # completed | paused_for_approval | policy_violation
AGENT_PENDING_TOOL = "agent.pending_tool"
AGENT_APPROVED = "agent.approved_tools"
CACHE_HIT = "cache.hit"
COST = "cost.usd"

MS_PER_NS = 1_000_000


@dataclass
class Recorder:
    """A tracer plus the exporter holding what it emitted.

    In production you add an OTLP exporter to the same provider and change nothing
    else. That is the entire argument for instrumenting against the standard.
    """

    tracer: Tracer
    provider: TracerProvider
    exporter: InMemorySpanExporter

    def spans(self) -> list[ReadableSpan]:
        return list(self.exporter.get_finished_spans())

    def named(self, name: str) -> list[ReadableSpan]:
        return [s for s in self.spans() if s.name == name]

    def reset(self) -> None:
        self.exporter.clear()


def recorder(service: str = "assistant", otlp_endpoint: str | None = None) -> Recorder:
    """A tracer wired to an in-memory exporter, always.

    When `otlp_endpoint` is set (in production, from `OTEL_EXPORTER_OTLP_ENDPOINT`),
    the SAME provider also gets an OTLP exporter, so spans ship to a collector
    without changing a line of instrumentation. The in-memory copy stays, so the
    span assertions in tests and the /health tier report keep working either way.
    The OTLP SDK is imported lazily so the fast tier never installs it.
    """
    provider = TracerProvider()
    exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    if otlp_endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint))
        )
    return Recorder(tracer=provider.get_tracer(service), provider=provider, exporter=exporter)


def traced_tool(tool: Tool, tracer: Tracer) -> Tool:
    """Return the same tool with its body wrapped in a span.

    The wrapper re-raises. An observability layer that swallows an exception has
    turned a visible failure into a silent wrong answer, which is a strictly worse
    outcome than the crash it "prevented".
    """

    def wrapped(*args: Any, **kwargs: Any) -> Any:
        with tracer.start_as_current_span(f"tool.{tool.name}") as span:
            span.set_attribute(TOOL_NAME, tool.name)
            span.set_attribute(TOOL_GATED, tool.requires_approval)
            try:
                out = tool.fn(*args, **kwargs)
            except Exception as exc:
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                raise
            span.set_status(Status(StatusCode.OK))
            return out

    return Tool(name=tool.name, fn=wrapped, requires_approval=tool.requires_approval, doc=tool.doc)


def traced_registry(registry: dict[str, Tool], tracer: Tracer) -> dict[str, Tool]:
    """Instrument every tool at once. Adding a tool cannot forget to be traced."""
    return {name: traced_tool(tool, tracer) for name, tool in registry.items()}


def traced_run(run: Any, goal: str, tracer: Tracer, **kwargs: Any) -> Any:
    """Wrap one agent run in a root span, with the loop's own outcome on it.

    `agent.step_count` and `agent.paused_for_approval` are the two attributes you
    will actually filter on later: a run that hit the step cap and a run that
    stopped for a human look identical in a latency chart and could not be more
    different in a review.

    The approval story rides along too: which grants were live when the run
    started (`agent.approved_tools`), which tool it is now waiting on
    (`agent.pending_tool`), and a single `agent.outcome` you can group a
    dashboard by without reconstructing it from three booleans.
    """
    with tracer.start_as_current_span("agent.run") as span:
        approvals = kwargs.get("approvals") or {}
        span.set_attribute(
            AGENT_APPROVED, sorted(name for name, granted in approvals.items() if granted)
        )
        result = run(goal, **kwargs)
        span.set_attribute(AGENT_STEPS, len(getattr(result, "audit", []) or []))
        pending = getattr(result, "pending", None)
        span.set_attribute(AGENT_PAUSED, pending is not None)
        if pending is not None:
            span.set_attribute(AGENT_PENDING_TOOL, pending.tool)
        if getattr(result, "fired_irreversible_tool_without_approval", False):
            span.set_attribute(AGENT_OUTCOME, "policy_violation")
            span.set_status(Status(StatusCode.ERROR, "gated tool fired without approval"))
        else:
            span.set_attribute(
                AGENT_OUTCOME, "paused_for_approval" if pending is not None else "completed"
            )
            span.set_status(Status(StatusCode.OK))
        return result


# --- read the answers off the spans ----------------------------------------


def duration_ms(span: ReadableSpan) -> float:
    if span.end_time is None or span.start_time is None:
        return 0.0
    return (span.end_time - span.start_time) / MS_PER_NS


def percentile(values: Sequence[float], p: float) -> float:
    """Nearest-rank: index is ceil(p/100 * n) - 1. Not `round()` — ties-to-even
    shifts exact ranks and reports the wrong P50/P99."""
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, math.ceil(p / 100 * len(ordered)) - 1))
    return ordered[idx]


def tool_calls(spans: Sequence[ReadableSpan]) -> list[str]:
    """Which tools ran, in order. The audit trail you didn't have to write."""
    return [
        str((s.attributes or {}).get(TOOL_NAME))
        for s in spans
        if (s.attributes or {}).get(TOOL_NAME) is not None
    ]


def time_by_tool(spans: Sequence[ReadableSpan]) -> dict[str, float]:
    """Where the wall clock went. Usually not where you assumed."""
    totals: dict[str, float] = {}
    for span in spans:
        name = (span.attributes or {}).get(TOOL_NAME)
        if name is not None:
            key = str(name)
            totals[key] = totals.get(key, 0.0) + duration_ms(span)
    return totals


def slowest_tool(spans: Sequence[ReadableSpan]) -> str | None:
    totals = time_by_tool(spans)
    return max(totals, key=lambda k: totals[k]) if totals else None


def failed_spans(spans: Sequence[ReadableSpan]) -> list[ReadableSpan]:
    return [s for s in spans if s.status.status_code is StatusCode.ERROR]


def gated_tool_calls(spans: Sequence[ReadableSpan]) -> list[str]:
    """Every irreversible tool that actually fired.

    This is a safety report, not a performance one. Phase 6 asked you to *contain*
    these; production asks you to prove which ones ran.
    """
    return [
        str((s.attributes or {}).get(TOOL_NAME))
        for s in spans
        if (s.attributes or {}).get(TOOL_GATED) is True
    ]
