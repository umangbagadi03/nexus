from types import SimpleNamespace

import pytest

from nexus import config
from nexus.llm import gemini_client

BUSY = Exception("503 UNAVAILABLE")
OUT_OF_QUOTA = Exception("429 RESOURCE_EXHAUSTED")


class FakeModels:
    def __init__(self, behaviour):
        self.behaviour = behaviour
        self.calls = []

    def respond(self, model):
        self.calls.append(model)
        result = self.behaviour[model]
        if isinstance(result, Exception):
            raise result
        return result

    def generate_content(self, model, contents, config):
        return SimpleNamespace(text=self.respond(model))

    def generate_content_stream(self, model, contents, config):
        return self.respond(model)


def make_client(monkeypatch, behaviour):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(config, "GEMINI_MODEL", "first")
    monkeypatch.setattr(config, "GEMINI_FALLBACK_MODELS", ["second"])
    monkeypatch.setattr(gemini_client, "WAIT_SECONDS", 0)

    client = gemini_client.GeminiClient()
    client.client = SimpleNamespace(models=FakeModels(behaviour))
    return client


def chunk(text):
    return SimpleNamespace(text=text)


def test_busy_model_falls_back_to_the_next(monkeypatch):
    client = make_client(monkeypatch, {"first": BUSY, "second": "answer"})
    assert client.generate("system", "user") == "answer"
    assert client.name == "Gemini (second)"


def test_stream_falls_back_when_out_of_quota(monkeypatch):
    client = make_client(monkeypatch, {"first": OUT_OF_QUOTA, "second": [chunk("a"), chunk("b")]})
    assert list(client.stream("system", "user")) == ["a", "b"]


def test_other_errors_do_not_fall_back(monkeypatch):
    client = make_client(monkeypatch, {"first": Exception("400 INVALID_ARGUMENT"), "second": "answer"})
    with pytest.raises(Exception, match="400"):
        client.generate("system", "user")
    assert client.client.models.calls == ["first"]


def test_stream_does_not_restart_after_text_was_sent(monkeypatch):
    def fails_midway():
        yield chunk("Hello ")
        raise BUSY

    client = make_client(monkeypatch, {"first": fails_midway(), "second": [chunk("again")]})
    pieces = []
    with pytest.raises(Exception, match="503"):
        for piece in client.stream("system", "user"):
            pieces.append(piece)
    assert pieces == ["Hello "]
    assert client.client.models.calls == ["first"]


def test_gives_up_when_every_model_stays_busy(monkeypatch):
    client = make_client(monkeypatch, {"first": BUSY, "second": OUT_OF_QUOTA})
    with pytest.raises(Exception):
        client.generate("system", "user")
    assert len(client.client.models.calls) == 2 * gemini_client.MAX_ATTEMPTS
