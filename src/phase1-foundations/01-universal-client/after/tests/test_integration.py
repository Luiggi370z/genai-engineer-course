"""Tier 2: the same four calls against a REAL local model. Needs Ollama running
with qwen3.5:9b pulled.

    make test-integration
"""
from __future__ import annotations

import pytest

from src.client import ToolCall, call_tool, complete, extract, stream

pytestmark = pytest.mark.integration

WEATHER_TOOL = {
    "name": "get_weather",
    "description": "Current weather for a city. Use it whenever a city's weather is asked.",
    "parameters": {
        "type": "object",
        "properties": {"city": {"type": "string"}},
        "required": ["city"],
    },
}


def test_complete_answers():
    out = complete("Reply with exactly the word: pong", provider="local")
    assert "pong" in out.lower()


def test_stream_arrives_in_more_than_one_piece():
    deltas = list(stream("Count from 1 to 10, digits separated by spaces.", provider="local"))
    assert len(deltas) > 1
    assert "5" in "".join(deltas)


def test_the_model_picks_the_offered_tool():
    result = call_tool("What is the weather in Lima right now?", [WEATHER_TOOL], provider="local")
    assert isinstance(result, ToolCall)
    assert result.name == "get_weather"
    assert "lima" in str(result.args.get("city", "")).lower()


def test_extract_returns_schema_valid_json():
    schema = {
        "type": "object",
        "properties": {"invoice_id": {"type": "string"}, "total": {"type": "number"}},
        "required": ["invoice_id", "total"],
    }
    out = extract(
        "Invoice INV-88102 has a total of 1250.50 EUR. Extract the fields.",
        schema,
        provider="local",
    )
    assert out["invoice_id"].upper().startswith("INV")
    assert isinstance(out["total"], int | float)
