"""Real OpenTelemetry spans, asserted offline. No collector, no vendor account.

This is the payoff of instrumenting against the standard: `InMemorySpanExporter`
is part of the SDK, so the production tracing code is the code under test here.
Delete an attribute from `observe.py` and this suite goes red — which is the only
thing that stops instrumentation quietly rotting away.
"""
from __future__ import annotations

import pytest
from opentelemetry.trace import StatusCode

from src.observe import (
    CACHE_HIT,
    COST,
    MODEL,
    PROMPT_TOKENS,
    SPAN_NAME,
    TIER,
    bill,
    cache_hit_rate,
    cost_alarm,
    emit_call,
    error_rate,
    latencies_ms,
    llm_span,
    p50,
    p95,
    p99,
    percentile,
    recorder,
    safe_to_promote,
    spend_by_tier,
    total_cost,
)

# What LLM latency actually looks like at 100 requests: a tight fast cluster, a
# handful of retrieval/retry stragglers, and one genuinely awful outlier.
SKEWED = [300.0] * 90 + [2100.0] * 9 + [8400.0]


@pytest.fixture
def rec():
    return recorder("test-service")


def load(rec, latencies=SKEWED, cost_each=0.001):
    for i, ms in enumerate(latencies):
        emit_call(
            rec.tracer,
            model="gpt-5.2",
            duration_ms=ms,
            cost_usd=cost_each,
            prompt_tokens=900,
            completion_tokens=120,
            start_ns=i * 1_000_000_000,
        )
    return rec.spans()


def test_a_traced_call_emits_one_span_with_the_convention_attributes(rec):
    with llm_span(rec.tracer, model="qwen3.5:8b", tier="local") as span:
        bill(span, prompt_tokens=900, completion_tokens=120, cost_usd=0.0)

    spans = rec.spans()
    assert len(spans) == 1
    attrs = spans[0].attributes or {}
    assert spans[0].name == SPAN_NAME
    assert attrs[MODEL] == "qwen3.5:8b"
    assert attrs[TIER] == "local"
    assert attrs[PROMPT_TOKENS] == 900
    assert attrs[COST] == 0.0
    assert spans[0].status.status_code is StatusCode.OK


def test_a_failed_call_is_recorded_and_still_raises(rec):
    """Observability must not change control flow — and must not lose the failure."""
    with pytest.raises(TimeoutError):
        with llm_span(rec.tracer, model="gpt-5.2"):
            raise TimeoutError("provider did not answer")

    span = rec.spans()[0]
    assert span.status.status_code is StatusCode.ERROR
    assert error_rate(rec.spans()) == 1.0


def test_latency_is_read_off_the_spans_not_from_a_side_channel(rec):
    spans = load(rec, latencies=[100, 200, 300])
    assert latencies_ms(spans) == pytest.approx([100.0, 200.0, 300.0])


def test_the_mean_hides_what_the_tail_shows(rec):
    """The whole argument for a P99 budget, in one assertion."""
    spans = load(rec)
    mean = sum(latencies_ms(spans)) / len(spans)
    assert mean == pytest.approx(543.0)  # "half a second, feels fast"
    assert p50(spans) == pytest.approx(300.0)
    assert p95(spans) == pytest.approx(2100.0)
    assert p99(spans) == pytest.approx(8400.0)  # one user in a hundred waits 8.4s
    assert p99(spans) > mean * 15


def test_ten_requests_cannot_produce_a_p95_worth_believing(rec):
    """A percentile is only as honest as the sample behind it.

    With ten samples the 95th and 99th percentile are both just the maximum — one
    unlucky request. Quote the sample size next to the number, or the number is
    decoration."""
    spans = load(rec, latencies=[280, 300, 310, 295, 305, 290, 2100, 315, 300, 8400])
    assert p95(spans) == p99(spans) == max(latencies_ms(spans))


def test_percentile_is_nearest_rank_and_safe_on_empty():
    assert percentile([10, 20, 30, 40], 50) == 20
    assert percentile([10, 20, 30, 40], 100) == 40
    assert percentile([], 99) == 0.0


def test_spend_is_summed_from_the_cost_attribute(rec):
    spans = load(rec, latencies=[300.0] * 10, cost_each=0.002)
    assert total_cost(spans) == pytest.approx(0.02)
    assert cost_alarm(spans, budget_usd=0.01)
    assert not cost_alarm(spans, budget_usd=1.0)


def test_spend_splits_by_tier_which_is_what_routing_decisions_need(rec):
    emit_call(rec.tracer, model="qwen3.5:8b", tier="local", duration_ms=300, cost_usd=0.0)
    emit_call(rec.tracer, model="gpt-5.2", tier="frontier", duration_ms=900, cost_usd=0.004)
    emit_call(rec.tracer, model="gpt-5.2", tier="frontier", duration_ms=950, cost_usd=0.006)
    assert spend_by_tier(rec.spans()) == pytest.approx({"local": 0.0, "frontier": 0.010})


def test_cache_hits_are_visible_in_the_trace(rec):
    emit_call(rec.tracer, model="gpt-5.2", duration_ms=5, cost_usd=0.0, cache_hit=True)
    emit_call(rec.tracer, model="gpt-5.2", duration_ms=900, cost_usd=0.004)
    assert cache_hit_rate(rec.spans()) == 0.5
    assert (rec.spans()[0].attributes or {})[CACHE_HIT] is True


def test_metrics_are_zero_rather_than_exploding_on_no_traffic(rec):
    assert (p99(rec.spans()), total_cost(rec.spans())) == (0.0, 0.0)
    assert error_rate(rec.spans()) == 0.0
    assert cache_hit_rate(rec.spans()) == 0.0


def test_rollback_guard_blocks_budget_bust():
    assert not safe_to_promote(new_p99_ms=2500, prev_p99_ms=1000, budget_ms=2000)


def test_rollback_guard_blocks_big_regression():
    assert not safe_to_promote(new_p99_ms=1900, prev_p99_ms=1000, budget_ms=2000)


def test_rollback_guard_allows_healthy_promote():
    assert safe_to_promote(new_p99_ms=1050, prev_p99_ms=1000, budget_ms=2000)
