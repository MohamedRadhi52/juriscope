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


def test_anthropic_request_and_normalized_answer(monkeypatch):
    sent = {}

    def fake_post(url, payload, headers):
        sent.update(url=url, payload=payload, headers=headers)
        return {
            "model": "claude-haiku-4-5-20251001",
            "content": [{"type": "text", "text": '{"question": "Q ?"}'}],
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }

    monkeypatch.setenv("ANTHROPIC_API_KEY", "cle-de-test")
    monkeypatch.setattr(providers, "post_json", fake_post)
    answer = providers.anthropic_complete("Écris une question.", "claude-haiku-4-5-20251001")
    assert sent["url"] == providers.ANTHROPIC_URL
    assert sent["headers"]["x-api-key"] == "cle-de-test"
    assert sent["payload"]["messages"] == [{"role": "user", "content": "Écris une question."}]
    assert answer == {
        "model": "claude-haiku-4-5-20251001",
        "output": '{"question": "Q ?"}',
        "usage": {"input_tokens": 10, "output_tokens": 5},
    }


def test_mistral_request_uses_json_mode_and_same_answer_shape(monkeypatch):
    sent = {}

    def fake_post(url, payload, headers):
        sent.update(payload=payload, headers=headers)
        return RESPONSE

    monkeypatch.setenv("MISTRAL_API_KEY", "cle-de-test")
    monkeypatch.setattr(providers, "post_json", fake_post)
    answer = providers.mistral_complete("Écris une question.", "mistral-large-latest")
    assert sent["payload"]["response_format"] == {"type": "json_object"}
    assert sent["headers"]["Authorization"] == "Bearer cle-de-test"
    assert answer == {
        "model": "mistral-large-2511",
        "output": '{"question": "Q ?"}',
        "usage": {"input_tokens": 10, "output_tokens": 5},
    }


def test_json_is_found_around_text_and_code_fences():
    raw = 'Voici la question :\n```json\n{"question": "Q ?", "extrait": "a b c"}\n```'
    assert providers.extract_json(raw) == {"question": "Q ?", "extrait": "a b c"}
    assert providers.extract_json("pas de JSON") is None


def test_cost_uses_the_public_prices():
    usages = [{"input_tokens": 600_000, "output_tokens": 100_000}] * 2
    assert providers.cost(usages, "claude-haiku-4-5-20251001") == 2.2


def test_azure_openai_uses_the_deployment_url_and_api_key(monkeypatch):
    sent = {}

    def fake_post(url, payload, headers):
        sent.update(url=url, headers=headers)
        return RESPONSE

    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://ressource.openai.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "cle-de-test")
    monkeypatch.setattr(providers, "post_json", fake_post)
    answer = providers.azure_openai_complete("Écris une question.", "mon-deploiement")
    assert sent["url"].startswith(
        "https://ressource.openai.azure.com/openai/deployments/mon-deploiement/chat/completions"
    )
    assert sent["headers"]["api-key"] == "cle-de-test"
    assert answer["usage"] == {"input_tokens": 10, "output_tokens": 5}


def test_anthropic_text_is_taken_after_a_thinking_block(monkeypatch):
    def fake_post(url, payload, headers):
        blocks = [{"type": "thinking", "thinking": "..."}, {"type": "text", "text": "ok"}]
        return {"model": "m", "content": blocks, "usage": {"input_tokens": 1, "output_tokens": 1}}

    monkeypatch.setenv("ANTHROPIC_API_KEY", "cle-de-test")
    monkeypatch.setattr(providers, "post_json", fake_post)
    assert providers.anthropic_complete("Q ?", "m")["output"] == "ok"


def test_retry_waits_as_long_as_the_api_asks(monkeypatch):
    waits, calls = [], []

    def fake_urlopen(request, timeout):
        calls.append(request)
        if len(calls) == 1:
            raise HTTPError(request.full_url, 429, "Too Many Requests", {"retry-after": "7"}, None)
        return io.BytesIO(json.dumps(RESPONSE).encode())

    monkeypatch.setattr(providers, "urlopen", fake_urlopen)
    monkeypatch.setattr(providers.time, "sleep", waits.append)
    providers.post_json("https://example.org", {}, {})
    assert waits == [7.0]


def test_temperature_is_sent_only_when_given(monkeypatch):
    sent = []

    def fake_post(url, payload, headers):
        sent.append(payload)
        blocks = [{"type": "text", "text": "ok"}]
        return {"model": "m", "content": blocks, "usage": {"input_tokens": 1, "output_tokens": 1}}

    monkeypatch.setenv("ANTHROPIC_API_KEY", "cle-de-test")
    monkeypatch.setattr(providers, "post_json", fake_post)
    providers.anthropic_complete("Q ?", "m")
    providers.anthropic_complete("Q ?", "m", temperature=0)
    assert "temperature" not in sent[0]
    assert sent[1]["temperature"] == 0
