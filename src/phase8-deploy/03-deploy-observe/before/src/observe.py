"""TODO: production observability on OpenTelemetry, plus a rollback guard.

The wiring is given (`recorder`) and so are the attribute constants. What's yours:

1) `llm_span` — a context manager that opens one span per model call, marks it OK
   or ERROR, and **re-raises**. Observability that changes control flow is a
   liability, and a failure with no trace is the one you'll need to debug.
2) `bill` / `emit_call` — attach the Phase-1 meter's numbers to the span, using
   the attribute constants below rather than names you invent inline.
3) The metrics — `latencies_ms`, `percentile`, `total_cost`, `error_rate`,
   `spend_by_tier`, `cache_hit_rate` — all derived **from the spans**. Resist
   keeping a second list of latencies: two sources of truth disagree eventually,
   and you will trust the wrong one.
4) `safe_to_promote` — block a build that busts the tail budget or regresses it.

Note what `recorder()` buys you: `InMemorySpanExporter` ships with the SDK, so the
production tracing code is testable with no collector and no vendor account. And
the production path is already wired: set `OTEL_EXPORTER_OTLP_ENDPOINT` and the
same provider also ships spans over OTLP, changing nothing else — that portability
is the entire reason to instrument against OTel rather than against a vendor's
client library.

Reference: ../after/src/observe.py.
"""
from __future__ import annotations

import os
from collections.abc import Sequence
from contextlib import contextmanager
from dataclasses import dataclass

from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import Tracer

# llm.model_name and llm.token_count.* are OpenInference semantic-convention
# names — use the agreed vocabulary where one exists. cost.usd, llm.tier and
# cache.hit are OUR extensions: no convention covers them, so they are labelled
# custom rather than passed off as standard.
MODEL = "llm.model_name"
PROMPT_TOKENS = "llm.token_count.prompt"
COMPLETION_TOKENS = "llm.token_count.completion"
COST = "cost.usd"
TIER = "llm.tier"
CACHE_HIT = "cache.hit"

SPAN_NAME = "llm.call"
MS_PER_NS = 1_000_000


@dataclass
class Recorder:
    """A tracer plus the in-memory exporter holding everything it emitted."""

    tracer: Tracer
    provider: TracerProvider
    exporter: InMemorySpanExporter

    def spans(self) -> list[ReadableSpan]:
        return list(self.exporter.get_finished_spans())

    def reset(self) -> None:
        self.exporter.clear()


def recorder(service: str = "assistant", otlp_endpoint: str | None = None) -> Recorder:
    """Wire a provider that keeps its spans in memory. No network, no vendor.

    Unless there is one: when `otlp_endpoint` — or, in production, the standard
    `OTEL_EXPORTER_OTLP_ENDPOINT` env var — is set, the SAME provider also ships
    every span over OTLP. The in-memory exporter stays either way, so tests and
    the metrics helpers below keep reading spans locally. The OTLP package is
    imported lazily; the fast tier never installs it (`--group integration` does).
    """
    provider = TracerProvider()
    exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    otlp_endpoint = otlp_endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint))
        )
    return Recorder(tracer=provider.get_tracer(service), provider=provider, exporter=exporter)


@contextmanager
def llm_span(tracer: Tracer, model: str, tier: str = "default"):
    """TODO 1: open a span named SPAN_NAME, set MODEL and TIER, yield it.

    On an exception: set an ERROR status and re-raise. On success: set OK.
    """
    raise NotImplementedError
    yield  # keeps this a generator; delete once implemented


def bill(span, prompt_tokens: int, completion_tokens: int, cost_usd: float) -> None:
    """TODO 2: attach token counts and dollars to the span that earned them."""
    raise NotImplementedError


def emit_call(
    tracer: Tracer,
    *,
    model: str,
    duration_ms: float,
    cost_usd: float = 0.0,
    tier: str = "default",
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    cache_hit: bool = False,
    ok: bool = True,
    start_ns: int = 0,
) -> None:
    """TODO 3: emit one finished span with an EXPLICIT duration.

    `tracer.start_span(name, start_time=...)` and `span.end(end_time=...)` take
    nanosecond timestamps. Passing them in is the same injected-clock trick used
    elsewhere in the course: it lets a test script a latency distribution instead
    of sleeping through one.
    """
    raise NotImplementedError


# --- metrics, derived from the spans and nowhere else -----------------------


def latencies_ms(spans: Sequence[ReadableSpan]) -> list[float]:
    """TODO 4: durations off the spans. OTel records nanoseconds."""
    raise NotImplementedError


def percentile(values: Sequence[float], p: float) -> float:
    """TODO 5: nearest-rank percentile, 0.0 on empty. No interpolation.
    The rank is ceil(p/100 * n) — not round(), which shifts ties to even."""
    raise NotImplementedError


def p50(spans: Sequence[ReadableSpan]) -> float:
    return percentile(latencies_ms(spans), 50)


def p95(spans: Sequence[ReadableSpan]) -> float:
    return percentile(latencies_ms(spans), 95)


def p99(spans: Sequence[ReadableSpan]) -> float:
    """The number that goes in the SLO. The mean describes nobody."""
    return percentile(latencies_ms(spans), 99)


def cost_of(span: ReadableSpan) -> float:
    """TODO 6: read COST off one span.

    Span attributes are a union of scalars *and* sequences, so narrow the type
    before calling `float()`. Return 0.0 when the attribute is missing — a span
    with no cost is an un-instrumented call, and crashing the dashboard over it
    hides the more useful signal that something stopped reporting.
    """
    raise NotImplementedError


def total_cost(spans: Sequence[ReadableSpan]) -> float:
    return sum(cost_of(span) for span in spans)


def cost_alarm(spans: Sequence[ReadableSpan], budget_usd: float) -> bool:
    """True once the budget is blown — catch a runaway before it catches you."""
    return total_cost(spans) > budget_usd


def error_rate(spans: Sequence[ReadableSpan]) -> float:
    """TODO 7: share of spans whose status is ERROR. 0.0 on no traffic."""
    raise NotImplementedError


def cache_hit_rate(spans: Sequence[ReadableSpan]) -> float:
    """TODO 8: share of spans with CACHE_HIT true. 0.0 on no traffic."""
    raise NotImplementedError


def spend_by_tier(spans: Sequence[ReadableSpan]) -> dict[str, float]:
    """TODO 9: dollars grouped by TIER — the input to every routing decision."""
    raise NotImplementedError


def safe_to_promote(new_p99_ms: float, prev_p99_ms: float, budget_ms: float) -> bool:
    """TODO 10: refuse a build over the budget, or one that regresses the tail
    badly against the release currently in production."""
    raise NotImplementedError
