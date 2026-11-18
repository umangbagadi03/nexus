from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from nexus import config
from nexus.api import workspace_routes
from nexus.llm import provider


def no_keys(monkeypatch):
    monkeypatch.setattr(config, "LLM_PROVIDER", "")
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "")
    monkeypatch.setattr(config, "OPENAI_API_KEY", "")


def test_no_key_and_no_ollama_means_search_only(monkeypatch):
    no_keys(monkeypatch)
    monkeypatch.setattr(provider, "ollama_is_running", always_false)
    assert provider.pick_provider_name() == "none"


def test_no_key_uses_ollama_when_it_runs(monkeypatch):
    no_keys(monkeypatch)
    monkeypatch.setattr(provider, "ollama_is_running", always_true)
    assert provider.pick_provider_name() == "ollama"


def test_none_in_settings_means_no_model(monkeypatch):
    monkeypatch.setattr(config, "LLM_PROVIDER", "none")
    monkeypatch.setattr(provider, "_llm", None)
    assert provider.get_llm() is None


def always_false():
    return False


def always_true():
    return True


def ask_request(provider_name, api_key):
    return SimpleNamespace(provider=provider_name, api_key=api_key, model="")


def test_visitor_key_builds_their_own_client(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "server-key")
    llm = workspace_routes.choose_llm(ask_request("gemini", " visitor-key "))
    assert llm.name.startswith("Gemini")
    # The server keeps its own model, the visitor's client is only for this question
    assert llm is not provider._llm


def test_unknown_provider_is_refused():
    with pytest.raises(HTTPException):
        workspace_routes.choose_llm(ask_request("ollama", "some-key"))


def test_errors_never_show_the_key():
    error = Exception("Request failed for key secret-123, try again")
    text = workspace_routes.error_text(error, "secret-123")
    assert "secret-123" not in text
    assert "[your key]" in text


def test_a_wrong_key_gets_a_plain_message():
    error = Exception("400 INVALID_ARGUMENT API_KEY_INVALID")
    text = workspace_routes.error_text(error, "abc")
    assert text.startswith("The provider did not accept this API key")
