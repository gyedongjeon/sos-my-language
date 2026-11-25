"""Feedback language, theme, and model settings."""

import importlib.util

import litellm
import pytest

from app.llm import LLMError, complete, format_conversation, llm_config, parse_json_reply
from app.settings import Settings, feedback_language


def test_feedback_language_is_unset_at_first(client):
    assert client.get("/api/settings").json()["feedback_language"] is None
    assert feedback_language() == "English"


def test_feedback_language_is_saved_and_cleared(client):
    assert client.put("/api/settings", json={"feedback_language": " Korean "}).json()["feedback_language"] == "Korean"
    assert feedback_language() == "Korean"
    client.put("/api/settings", json={"feedback_language": None})
    assert client.get("/api/settings").json()["feedback_language"] is None


def test_the_theme_follows_the_system_at_first(client):
    assert client.get("/api/settings").json()["theme"] == ""


def test_a_chosen_theme_is_saved_and_leaves_the_language_alone(client):
    client.put("/api/settings", json={"feedback_language": "Korean"})
    assert client.put("/api/settings", json={"theme": "sos-night"}).json() == {
        "feedback_language": "Korean",
        "theme": "sos-night",
    }
    # Choosing the language again keeps the theme.
    client.put("/api/settings", json={"feedback_language": "Japanese"})
    assert client.get("/api/settings").json() == {"feedback_language": "Japanese", "theme": "sos-night"}


def test_an_unknown_theme_is_refused(client):
    assert client.put("/api/settings", json={"theme": "neon"}).status_code == 422


def test_feedback_language_falls_back_to_the_environment(monkeypatch):
    monkeypatch.setenv("FEEDBACK_LANGUAGE", "Japanese")
    assert feedback_language() == "Japanese"


def test_no_model_is_configured_at_first(client):
    assert client.get("/api/settings/llm").json() == {"model": None, "source": None, "key_hint": None}


def test_saved_key_is_never_sent_back(client):
    saved = client.put("/api/settings/llm", json={"model": "gemini/flash", "api_key": " secret-key-1234 "}).json()
    assert saved == {"model": "gemini/flash", "source": "app", "key_hint": "1234"}
    assert "secret" not in client.get("/api/settings/llm").text
    assert llm_config() == ("gemini/flash", "secret-key-1234")


def test_a_new_model_needs_a_key(client):
    response = client.put("/api/settings/llm", json={"model": "gemini/flash"})
    assert response.status_code == 422
    assert llm_config() == ("", None)


def test_key_is_kept_while_the_provider_stays_the_same(client):
    client.put("/api/settings/llm", json={"model": "gemini/flash", "api_key": "key-1"})
    assert client.put("/api/settings/llm", json={"model": "gemini/pro"}).status_code == 200
    assert llm_config() == ("gemini/pro", "key-1")


def test_another_provider_needs_its_own_key(client):
    client.put("/api/settings/llm", json={"model": "gemini/flash", "api_key": "key-1"})
    assert client.put("/api/settings/llm", json={"model": "openai/gpt"}).status_code == 422
    assert llm_config() == ("gemini/flash", "key-1")


@pytest.mark.parametrize("model", ["flash", "gemini/", "/flash", "gemini/fl ash"])
def test_model_must_be_written_as_provider_slash_model(client, model):
    assert client.put("/api/settings/llm", json={"model": model, "api_key": "k"}).status_code == 422


def test_removing_the_model_falls_back_to_the_environment(client, monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "anthropic/claude")
    client.put("/api/settings/llm", json={"model": "gemini/flash", "api_key": "key-1"})
    assert client.delete("/api/settings/llm").json() == {
        "model": "anthropic/claude",
        "source": "env",
        "key_hint": None,
    }


def test_testing_without_a_model_explains_what_to_do(client):
    response = client.post("/api/settings/llm/test")
    assert response.status_code == 502
    assert "Settings page" in response.json()["detail"]


def fake_reply(text):
    message = type("Message", (), {"content": text})
    return type("Response", (), {"choices": [type("Choice", (), {"message": message})]})


def test_test_request_uses_the_saved_model_and_key(client, monkeypatch):
    calls = []
    monkeypatch.setattr(litellm, "completion", lambda **kwargs: calls.append(kwargs) or fake_reply("OK"))
    client.put("/api/settings/llm", json={"model": "gemini/flash", "api_key": "key-1"})
    assert client.post("/api/settings/llm/test").status_code == 204
    assert calls[0]["model"] == "gemini/flash"
    assert calls[0]["api_key"] == "key-1"


def test_empty_reply_is_an_error(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "gemini/flash")
    monkeypatch.setattr(litellm, "completion", lambda **kwargs: fake_reply("  "))
    with pytest.raises(LLMError, match="empty reply"):
        complete("system", "user")


def test_provider_failures_become_user_facing_errors(monkeypatch):
    def fail(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setenv("LLM_MODEL", "gemini/flash")
    monkeypatch.setattr(litellm, "completion", fail)
    with pytest.raises(LLMError, match="gemini/flash: boom"):
        complete("system", "user")


def test_retries_have_the_package_they_need():
    # LiteLLM retries a failed request (num_retries) with tenacity but does not install it.
    # Without it, any failed request is reported as "tenacity import failed" instead of its cause.
    assert importlib.util.find_spec("tenacity") is not None


def test_json_reply_may_be_wrapped_in_a_code_fence():
    reply = '```json\n{"feedback_language": "Korean"}\n```'
    assert parse_json_reply(reply, Settings).feedback_language == "Korean"


def test_json_reply_in_the_wrong_shape_is_an_error():
    with pytest.raises(LLMError, match="unexpected format"):
        parse_json_reply('{"feedback_language": 3}', Settings)


def test_conversation_is_rendered_one_line_per_message():
    messages = [("Tutor", "How was your weekend?"), ("Learner", "I go to the beach.")]
    assert format_conversation(messages) == "Tutor: How was your weekend?\nLearner: I go to the beach."
