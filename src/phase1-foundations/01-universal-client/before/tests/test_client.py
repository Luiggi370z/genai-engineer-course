"""Fast tier: no model, no keys, no network. The SDK clients are swapped for
fakes so what is actually under test is the part this lesson owns — the
provider table and the normalization of text, streams, tool calls and
structured output into one shape per capability."""
from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

import src.client as client
from src.client import PROVIDERS, Provider, ToolCall, call_tool, complete, extract, stream

WEATHER_TOOL = {
    "name": "get_weather",
    "description": "Current weather for a city.",
    "parameters": {
        "type": "object",
        "properties": {"city": {"type": "string"}},
        "required": ["city"],
    },
}


# --- fakes that mimic each SDK's response shapes ----------------------------


class FakeOpenAI:
    """Stands in for openai.OpenAI. Scripted per test via class attributes."""

    text: str | None = "hello from the fake"
    tool_calls: list[Any] | None = None
    deltas: list[str | None] = []

    def __init__(self) -> None:
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))
        self.last_kwargs: dict[str, Any] = {}

    def _create(self, **kwargs: Any) -> Any:
        self.last_kwargs = kwargs
        FakeOpenAI.last_instance = self
        if kwargs.get("stream"):
            return [
                SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=d))])
                if d is not None
                else SimpleNamespace(choices=[])  # a usage frame with no choices
                for d in self.deltas
            ]
        message = SimpleNamespace(content=self.text, tool_calls=self.tool_calls)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeAnthropic:
    """Stands in for anthropic.Anthropic."""

    blocks: list[Any] = []
    deltas: list[str] = []

    def __init__(self) -> None:
        self.messages = SimpleNamespace(create=self._create, stream=self._stream)

    def _create(self, **kwargs: Any) -> Any:
        FakeAnthropic.last_kwargs = kwargs
        return SimpleNamespace(content=self.blocks)

    def _stream(self, **kwargs: Any) -> Any:
        deltas = self.deltas

        class Ctx:
            text_stream = iter(deltas)

            def __enter__(self) -> Any:
                return self

            def __exit__(self, *exc: Any) -> None:
                return None

        return Ctx()


@pytest.fixture(autouse=True)
def fake_sdks(monkeypatch):
    monkeypatch.setattr(client, "_openai_client", lambda p: FakeOpenAI())
    monkeypatch.setattr(client, "_anthropic_client", lambda p: FakeAnthropic())
    FakeOpenAI.text = "hello from the fake"
    FakeOpenAI.tool_calls = None
    FakeOpenAI.deltas = []
    FakeAnthropic.blocks = []
    FakeAnthropic.deltas = []


# --- the provider table is config, not code --------------------------------


def test_every_provider_is_configured_not_hardcoded():
    for name in ("gpt", "claude", "gemini", "local", "mlx"):
        p = PROVIDERS[name]
        assert isinstance(p, Provider)
        assert p.model, f"{name} has no model string"


def test_openai_compatible_providers_share_one_adapter():
    # gpt, gemini, local and mlx all ride the OpenAI wire format; only the
    # base_url differs. That is the whole argument of the lesson.
    assert PROVIDERS["gpt"].base_url is None
    assert "generativelanguage.googleapis.com" in (PROVIDERS["gemini"].base_url or "")
    assert PROVIDERS["local"].base_url == "http://localhost:11434/v1"
    assert PROVIDERS["mlx"].base_url == "http://localhost:8080/v1"


# --- complete ---------------------------------------------------------------


def test_complete_returns_text_for_openai_compatible_providers():
    for provider in ("gpt", "gemini", "local", "mlx"):
        assert complete("hi", provider=provider) == "hello from the fake"


def test_complete_concatenates_anthropic_text_blocks():
    FakeAnthropic.blocks = [
        SimpleNamespace(type="text", text="hello "),
        SimpleNamespace(type="tool_use", name="x", input={}),
        SimpleNamespace(type="text", text="world"),
    ]
    assert complete("hi", provider="claude") == "hello world"


# --- stream -----------------------------------------------------------------


def test_stream_yields_deltas_and_skips_empty_frames():
    FakeOpenAI.deltas = ["hel", None, "lo", ""]  # None = usage frame, "" = empty delta
    assert "".join(stream("hi", provider="local")) == "hello"


def test_stream_normalizes_anthropic_to_the_same_shape():
    FakeAnthropic.deltas = ["hel", "lo"]
    assert "".join(stream("hi", provider="claude")) == "hello"


# --- call_tool ---------------------------------------------------------------


def test_tool_calls_normalize_to_one_shape_across_providers():
    FakeOpenAI.tool_calls = [
        SimpleNamespace(
            function=SimpleNamespace(name="get_weather", arguments=json.dumps({"city": "Lima"}))
        )
    ]
    FakeAnthropic.blocks = [
        SimpleNamespace(type="tool_use", name="get_weather", input={"city": "Lima"})
    ]

    for provider in ("local", "claude"):
        result = call_tool("weather in Lima?", [WEATHER_TOOL], provider=provider)
        assert result == ToolCall(name="get_weather", args={"city": "Lima"})


def test_call_tool_returns_plain_text_when_the_model_declines():
    FakeOpenAI.tool_calls = None
    FakeOpenAI.text = "it never rains in Lima"
    assert call_tool("weather?", [WEATHER_TOOL], provider="local") == "it never rains in Lima"


def test_tools_are_adapted_to_each_wire_format():
    call_tool("weather?", [WEATHER_TOOL], provider="local")
    sent = FakeOpenAI.last_instance.last_kwargs["tools"][0]
    assert sent == {"type": "function", "function": WEATHER_TOOL}

    FakeAnthropic.blocks = [SimpleNamespace(type="text", text="dry")]
    call_tool("weather?", [WEATHER_TOOL], provider="claude")
    sent = FakeAnthropic.last_kwargs["tools"][0]
    assert sent["input_schema"] == WEATHER_TOOL["parameters"]


# --- extract ------------------------------------------------------------------

INVOICE_SCHEMA = {
    "type": "object",
    "properties": {"invoice_id": {"type": "string"}, "total": {"type": "number"}},
    "required": ["invoice_id", "total"],
}


def test_extract_parses_schema_valid_json():
    FakeOpenAI.text = json.dumps({"invoice_id": "INV-1", "total": 42.5})
    out = extract("...", INVOICE_SCHEMA, provider="local")
    assert out == {"invoice_id": "INV-1", "total": 42.5}


def test_extract_uses_the_forced_tool_idiom_on_anthropic():
    FakeAnthropic.blocks = [
        SimpleNamespace(
            type="tool_use", name="extract", input={"invoice_id": "INV-1", "total": 42.5}
        )
    ]
    assert extract("...", INVOICE_SCHEMA, provider="claude")["invoice_id"] == "INV-1"
    assert FakeAnthropic.last_kwargs["tool_choice"] == {"type": "tool", "name": "extract"}


def test_extract_refuses_a_reply_missing_required_fields():
    FakeOpenAI.text = json.dumps({"invoice_id": "INV-1"})  # no total
    with pytest.raises(ValueError, match="total"):
        extract("...", INVOICE_SCHEMA, provider="local")
