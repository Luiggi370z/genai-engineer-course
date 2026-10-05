from src.meter import Usage, cost, count_openai


def test_tiktoken_counts_something():
    assert count_openai("hello world") > 0


def test_cost_uses_the_usage_object():
    u = Usage(input_tokens=1_000_000, output_tokens=0)
    assert cost("claude-sonnet-4-6", u) == 3.00  # $3 / MTok input


def test_cached_tokens_are_cheaper():
    fresh = Usage(input_tokens=1000, output_tokens=0)
    cached = Usage(input_tokens=1000, output_tokens=0, cache_read_input_tokens=1000)
    assert cost("claude-sonnet-4-6", cached) < cost("claude-sonnet-4-6", fresh)


def test_anthropic_input_tokens_are_already_uncached():
    """A shape that goes negative if you subtract cache_read from input_tokens.

    200_000 uncached + 800_000 read from cache. Anthropic reports those as two
    fields. input_tokens here is only the uncached part.
    """
    usage = Usage(
        input_tokens=200_000,
        output_tokens=0,
        cache_read_input_tokens=800_000,
        input_includes_cache=False,
    )
    billed = cost("claude-sonnet-4-6", usage)
    assert billed > 0
    assert usage.input_tokens == 200_000
    assert usage.cache_read_input_tokens == 800_000


def test_output_costs_more_than_input():
    only_in = Usage(input_tokens=1000, output_tokens=0)
    only_out = Usage(input_tokens=0, output_tokens=1000)
    assert cost("claude-sonnet-4-6", only_out) > cost("claude-sonnet-4-6", only_in)
