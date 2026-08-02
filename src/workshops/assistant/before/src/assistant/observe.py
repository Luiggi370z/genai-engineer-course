"""TODO: Workshop 8 layer — OpenTelemetry around the agent loop and every tool.

An agent is harder to observe than a single model call, because the interesting
question is never "how long did that take". It is *what did it do* — which tools, in
what order, how many steps, and where the eight seconds actually went. A timer on
`run()` cannot answer any of that; a span tree can.

The wiring is given. Yours:

1) traced_tool / traced_registry — wrap the tools at the **seam**. No tool should
   know it is being traced, which is what stops a newly-added tool from forgetting.
2) traced_run — a root span per run, carrying step count and whether it paused.
3) The readers — tool_calls, time_by_tool, slowest_tool, failed_spans,
   gated_tool_calls — all derived from the spans.

Use the attribute names defined below rather than inventing your own: agreed names
are what let a dashboard that has never seen this repo read your trace.

Reference: ../../after/src/assistant/observe.py.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import Tracer

from assistant.tools import Tool

# tool.name follows OpenInference's tool-span convention; the agent.*, cache.hit
# and cost.usd names are OUR extensions — labelled custom, not passed off as
# standard.
TOOL_NAME = "tool.name"
TOOL_GATED = "tool.requires_approval"
AGENT_STEPS = "agent.step_count"
AGENT_PAUSED = "agent.paused_for_approval"
AGENT_OUTCOME = "agent.outcome"  # completed | paused_for_approval | policy_violation
AGENT_PENDING_TOOL = "agent.pending_tool"
AGENT_APPROVED = "agent.approved_tools"
AGENT_APPROVAL_IDS = "agent.approval_ids"
CACHE_HIT = "cache.hit"
COST = "cost.usd"

MS_PER_NS = 1_000_000


@dataclass
class Recorder:
    """A tracer plus the exporter holding what it emitted.

    In production you add an OTLP exporter to the same provider and change nothing
    else. That portability is the whole argument for instrumenting against OTel
    instead of against a vendor's client library.
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
    """A tracer wired to an in-memory exporter, always. When `otlp_endpoint` is set
    (in production, from `OTEL_EXPORTER_OTLP_ENDPOINT`), the same provider also gets
    an OTLP exporter, so spans ship to a collector with no change to instrumentation.
    The OTLP SDK is imported lazily so the fast tier never installs it."""
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
    """TODO 1: return the same tool with its body wrapped in a span.

    Name the span `tool.<name>`, set TOOL_NAME and TOOL_GATED, and mark the span
    ERROR on an exception — then **re-raise**. An observability layer that swallows
    an exception has turned a visible failure into a silent wrong answer, which is
    strictly worse than the crash it "prevented".
    """
    raise NotImplementedError


def traced_registry(registry: dict[str, Tool], tracer: Tracer) -> dict[str, Tool]:
    """TODO 2: instrument every tool at once, so adding one cannot forget to."""
    raise NotImplementedError


def traced_run(run: Any, goal: str, tracer: Tracer, **kwargs: Any) -> Any:
    """TODO 3: wrap one agent run in an `agent.run` root span.

    Set AGENT_STEPS and AGENT_PAUSED — those are the two attributes you will
    actually filter on later, because a run that stopped for a human and a run that
    hit the step cap look identical on a latency chart and could not be more
    different in a review. Mark the span ERROR on a containment breach.

    Then put the approval story on the same span: AGENT_APPROVED = the sorted
    names in `kwargs["approvals"]` whose grant is truthy (set it BEFORE calling
    `run` — it describes what the run started with), AGENT_PENDING_TOOL = the
    tool a paused run is waiting on, and AGENT_OUTCOME = one of "completed",
    "paused_for_approval" or "policy_violation", so a dashboard can group runs
    without reconstructing the outcome from three booleans.

    A run driven by a consuming approval store has no allow-list to read, so when
    `result.approval_ids` is non-empty use it instead: AGENT_APPROVED = its sorted
    keys, AGENT_APPROVAL_IDS = the matching grant ids. Recording the id is what
    makes an approval auditable end to end — the same id appears on the /approve
    response, in the audit log and here, so "who authorized this send?" is a
    lookup rather than a reconstruction.
    """
    raise NotImplementedError


# --- read the answers off the spans ----------------------------------------


def duration_ms(span: ReadableSpan) -> float:
    """TODO 4: span duration in milliseconds. OTel stores nanoseconds."""
    raise NotImplementedError


def percentile(values: Sequence[float], p: float) -> float:
    """TODO 5: nearest-rank percentile, 0.0 on empty.
    The rank is ceil(p/100 * n) — not round(), which shifts ties to even."""
    raise NotImplementedError


def tool_calls(spans: Sequence[ReadableSpan]) -> list[str]:
    """TODO 6: which tools ran, in order — the audit trail you didn't have to write."""
    raise NotImplementedError


def time_by_tool(spans: Sequence[ReadableSpan]) -> dict[str, float]:
    """TODO 7: milliseconds per tool. Usually not where you assumed."""
    raise NotImplementedError


def slowest_tool(spans: Sequence[ReadableSpan]) -> str | None:
    """TODO 8: the worst offender, or None on an empty trace."""
    raise NotImplementedError


def failed_spans(spans: Sequence[ReadableSpan]) -> list[ReadableSpan]:
    """TODO 9: spans whose status is ERROR."""
    raise NotImplementedError


def gated_tool_calls(spans: Sequence[ReadableSpan]) -> list[str]:
    """TODO 10: every irreversible tool that actually fired.

    This is a safety report, not a performance one. Phase 6 asked you to *contain*
    these; production asks you to prove which ones ran. The caching layer in
    `cache.py` reads this to decide what it is allowed to store.
    """
    raise NotImplementedError
