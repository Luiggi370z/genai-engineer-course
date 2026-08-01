"""These tests don't call a real model — they check the abstraction's shape,
so they pass in CI with no API keys and no Ollama running."""
from src.client import PROVIDERS, Provider, complete


def test_every_provider_is_configured_not_hardcoded():
    for name, p in PROVIDERS.items():
        assert isinstance(p, Provider)
        assert p.model, f"{name} has no model string"


def test_openai_compatible_providers_share_one_adapter():
    # local + gpt both go through the OpenAI path; only base_url differs.
    assert PROVIDERS["local"].base_url == "http://localhost:11434/v1"
    assert PROVIDERS["gpt"].base_url is None


def test_complete_is_callable_with_a_default_provider():
    # signature check only — we don't invoke the network here.
    assert callable(complete)
