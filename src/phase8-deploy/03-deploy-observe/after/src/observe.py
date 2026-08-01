"""Production observability on OpenTelemetry — the portable layer, not a vendor SDK.

Two ideas carry this module.

**Instrument once.** Every LLM observability product (Langfuse v4, Phoenix,
Braintrust, your existing APM) either speaks OTel or exports to it. So the spans
are plain OTel spans carrying the OpenInference attribute names, and *where they
ship* really is an environment variable: `recorder()` reads
`OTEL_EXPORTER_OTLP_ENDPOINT` and, when set, adds an OTLP exporter to the same
provider. Nothing else in this file changes between a unit test and production.

**Read your metrics off the spans.** P95, spend and error rate are derived from the
exported spans rather than from a parallel bookkeeping list. The moment latency
lives in one place and traces in another they disagree, and you will trust the
wrong one. This also makes the whole layer unit-testable with no collector — which
is the only reason tracing code ever stays correct, because nothing fails when
instrumentation silently stops recording.
"""
from __future__ import annotations

import math
import os
from collections.abc import Sequence
from contextlib import contextmanager
from dataclasses import dataclass

from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import Status, StatusCode, Tracer

# llm.model_name and llm.token_count.* are OpenInference semantic-convention
# names — agreed vocabulary a dashboard can read without ever seeing this repo.
# (OTel's own GenAI conventions use gen_ai.*; pick one family and stick to it.)
MODEL = "llm.model_name"
PROMPT_TOKENS = "llm.token_count.prompt"
COMPLETION_TOKENS = "llm.token_count.completion"
# cost.usd, llm.tier and cache.hit are OUR extensions — no convention covers
# them. Custom names are fine; passing them off as standard is not.
COST = "cost.usd"
TIER = "llm.tier"
CACHE_HIT = "cache.hit"

SPAN_NAME = "llm.call"
MS_PER_NS = 1_000_000


@dataclass
class Recorder:
    """A tracer plus the in-memory exporter holding everything it emitted.

    This is the *test and CI* wiring. In production you register an OTLP exporter
    against the same provider and delete nothing else.
    """

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
    """Wrap one model call. Errors are recorded on the span, then re-raised.

    Marking the span ERROR rather than swallowing the exception matters: an
    observability layer that changes your control flow is a liability, and a
    failed request that leaves no trace is the one you will need to debug.
    """
    with tracer.start_as_current_span(SPAN_NAME) as span:
        span.set_attribute(MODEL, model)
        span.set_attribute(TIER, tier)
        try:
            yield span
        except Exception as exc:
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise
        span.set_status(Status(StatusCode.OK))


def bill(span, prompt_tokens: int, completion_tokens: int, cost_usd: float) -> None:
    """Attach the Phase-1 meter's output to the span that earned it."""
    span.set_attribute(PROMPT_TOKENS, prompt_tokens)
    span.set_attribute(COMPLETION_TOKENS, completion_tokens)
    span.set_attribute(COST, cost_usd)


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
    """Emit one finished `llm.call` span with an explicit duration.

    The timestamps are parameters, which is the same injected-clock trick the rest
    of the course uses: it lets tests and load simulations script a latency
    distribution without sleeping through it.
    """
    span = tracer.start_span(SPAN_NAME, start_time=start_ns)
    span.set_attribute(MODEL, model)
    span.set_attribute(TIER, tier)
    span.set_attribute(CACHE_HIT, cache_hit)
    bill(span, prompt_tokens, completion_tokens, cost_usd)
    span.set_status(Status(StatusCode.OK) if ok else Status(StatusCode.ERROR, "call failed"))
    span.end(end_time=start_ns + int(duration_ms * MS_PER_NS))


# --- metrics, derived from the spans and nowhere else -----------------------


def latencies_ms(spans: Sequence[ReadableSpan]) -> list[float]:
    """Durations straight off the spans — OTel records nanoseconds."""
    return [
        (span.end_time - span.start_time) / MS_PER_NS
        for span in spans
        if span.end_time is not None and span.start_time is not None
    ]


def percentile(values: Sequence[float], p: float) -> float:
    """Nearest-rank percentile. No interpolation: with 20 samples, invented
    values between the ones you measured are just a smoother-looking guess.

    The rank is `ceil(p/100 * n)` — the textbook definition. Do not reach for
    `round()`: Python rounds ties to even, which shifts the index on exact-rank
    ties (P50 of two samples would report the max) and quietly corrupts the very
    P99 this module exists to defend."""
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, math.ceil(p / 100 * len(ordered)) - 1))
    return ordered[idx]


def p50(spans: Sequence[ReadableSpan]) -> float:
    return percentile(latencies_ms(spans), 50)


def p95(spans: Sequence[ReadableSpan]) -> float:
    return percentile(latencies_ms(spans), 95)


def p99(spans: Sequence[ReadableSpan]) -> float:
    """The number that goes in the SLO. The mean describes nobody."""
    return percentile(latencies_ms(spans), 99)


def cost_of(span: ReadableSpan) -> float:
    """Span attributes are a union of scalars and sequences, so narrow before use.

    Returning 0.0 for a missing or non-numeric value is deliberate: a span with no
    cost attribute is an un-instrumented call, and crashing the dashboard over it
    hides the far more useful signal that something isn't reporting.
    """
    value = (span.attributes or {}).get(COST)
    return float(value) if isinstance(value, int | float) else 0.0


def total_cost(spans: Sequence[ReadableSpan]) -> float:
    return sum(cost_of(span) for span in spans)


def cost_alarm(spans: Sequence[ReadableSpan], budget_usd: float) -> bool:
    """True once the budget is blown — catch a runaway before it catches you."""
    return total_cost(spans) > budget_usd


def error_rate(spans: Sequence[ReadableSpan]) -> float:
    if not spans:
        return 0.0
    failed = sum(1 for s in spans if s.status.status_code is StatusCode.ERROR)
    return failed / len(spans)


def cache_hit_rate(spans: Sequence[ReadableSpan]) -> float:
    if not spans:
        return 0.0
    hits = sum(1 for s in spans if (s.attributes or {}).get(CACHE_HIT) is True)
    return hits / len(spans)


def spend_by_tier(spans: Sequence[ReadableSpan]) -> dict[str, float]:
    """Where the money actually goes. The input to every routing decision."""
    totals: dict[str, float] = {}
    for span in spans:
        tier = str((span.attributes or {}).get(TIER, "unknown"))
        totals[tier] = totals.get(tier, 0.0) + cost_of(span)
    return totals


def safe_to_promote(new_p99_ms: float, prev_p99_ms: float, budget_ms: float) -> bool:
    """Rollback guard: block a build that busts the tail budget, or that regresses
    the tail badly against the release currently in production."""
    if new_p99_ms > budget_ms:
        return False
    return new_p99_ms <= prev_p99_ms * 1.2  # tolerate drift, block a real regression


if __name__ == "__main__":
    rec = recorder()
    # A right-skewed distribution over 100 requests, which is what LLM latency
    # actually looks like: a fast majority, some stragglers, two genuinely awful ones.
    for i, ms in enumerate([300.0] * 89 + [2100.0] * 9 + [8400.0] * 2):
        emit_call(
            rec.tracer,
            model="qwen3.5:9b" if ms < 1000 else "gpt-5.2",
            tier="local" if ms < 1000 else "frontier",
            duration_ms=ms,
            cost_usd=0.0 if ms < 1000 else 0.004,
            prompt_tokens=900,
            completion_tokens=120,
            start_ns=i * 1_000_000_000,
        )
    spans = rec.spans()
    mean = sum(latencies_ms(spans)) / len(spans)
    print(f"mean {mean:.0f}ms  <- describes nobody")
    print(f"p50 {p50(spans):.0f}ms · p95 {p95(spans):.0f}ms · p99 {p99(spans):.0f}ms")
    print(f"spend ${total_cost(spans):.4f} by tier: {spend_by_tier(spans)}")
