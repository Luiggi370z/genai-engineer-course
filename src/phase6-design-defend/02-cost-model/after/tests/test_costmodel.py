from src.costmodel import Workload, daily_cost

W = Workload(queries_per_day=100_000, in_tokens=1500, out_tokens=500)


def test_cache_reduces_cost():
    assert daily_cost(W, cache_hit_rate=0.4) < daily_cost(W)


def test_local_routing_reduces_cost():
    assert daily_cost(W, local_share=0.5) < daily_cost(W)


def test_cache_then_route_roughly_halves_bill():
    base = daily_cost(W)
    tuned = daily_cost(W, cache_hit_rate=0.4, local_share=0.5)
    assert tuned <= base * 0.55
