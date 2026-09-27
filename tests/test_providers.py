import io
import json
from urllib.error import HTTPError

import pytest

from juriscope.generate import providers

RESPONSE = {
    "model": "mistral-large-2511",
    "choices": [{"message": {"content": '{"question": "Q ?"}'}}],
    "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
}


def test_post_json_waits_and_retries_on_rate_limit(monkeypatch):
    calls = []

    def fake_urlopen(request, timeout):
        calls.append(request)
        if len(calls) == 1:
            raise HTTPError(request.full_url, 429, "Too Many Requests", {}, None)
        return io.BytesIO(json.dumps(RESPONSE).encode())

    monkeypatch.setattr(providers, "urlopen", fake_urlopen)
    monkeypatch.setattr(providers.time, "sleep", lambda seconds: None)
    assert providers.post_json("https://example.org", {}, {}) == RESPONSE
    assert len(calls) == 2


def test_client_errors_are_not_retried_and_show_the_api_message(monkeypatch):
    calls = []

    def fake_urlopen(request, timeout):
        calls.append(request)
        body = io.BytesIO(b'{"message": "Unauthorized"}')
        raise HTTPError(request.full_url, 401, "Unauthorized", {}, body)

    monkeypatch.setattr(providers, "urlopen", fake_urlopen)
    with pytest.raises(RuntimeError, match="a répondu 401") as error:
        providers.post_json("https://example.org", {}, {})
    assert '"message": "Unauthorized"' in str(error.value)
    assert len(calls) == 1
    assert calls[0].get_header("User-agent") == "juriscope"


def test_mistral_json_sends_json_mode_and_returns_usage(monkeypatch):
    sent = {}

    def fake_post(url, payload, headers):
        sent.update(url=url, payload=payload, headers=headers)
        return RESPONSE

    monkeypatch.setenv("MISTRAL_API_KEY", "cle-de-test")
    monkeypatch.setattr(providers, "post_json", fake_post)
    answer = providers.mistral_json("Écris une question.", "mistral-large-latest", seed=7)
    assert sent["payload"]["response_format"] == {"type": "json_object"}
    assert sent["payload"]["random_seed"] == 7
    assert sent["headers"]["Authorization"] == "Bearer cle-de-test"
    assert answer == {
        "model": "mistral-large-2511",
        "output": '{"question": "Q ?"}',
        "usage": RESPONSE["usage"],
    }
