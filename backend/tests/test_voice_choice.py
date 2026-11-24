"""The partner's voice can be chosen on the Settings page among Kokoro's English voices."""

from app import speech
from tests.test_speech import voice_model  # noqa: F401  (fixture)


def test_the_voices_are_listed_with_the_default_chosen(client):
    voices = client.get("/api/voices").json()
    assert [v["id"] for v in voices][0] == speech.DEFAULT_VOICE
    assert {v["id"] for v in voices} >= {"af_bella", "am_michael", "bf_emma", "bm_george"}
    assert all(v["label"] for v in voices)
    assert [v["id"] for v in voices if v["chosen"]] == [speech.DEFAULT_VOICE]


def test_a_chosen_voice_reads_the_lines(client, voice_model):  # noqa: F811
    response = client.put("/api/voice", json={"voice": "am_michael"})
    assert response.status_code == 200, response.text
    assert [v["id"] for v in response.json() if v["chosen"]] == ["am_michael"]
    speech.synthesize("How was your weekend?")
    assert voice_model.calls == ["am_michael: How was your weekend?"]


def test_a_british_voice_speaks_british_english(client, voice_model):  # noqa: F811
    client.put("/api/voice", json={"voice": "bf_emma"})
    speech.synthesize("How was your weekend?")
    assert voice_model.langs == ["en-gb"]


def test_an_american_voice_speaks_american_english(voice_model):  # noqa: F811
    speech.synthesize("How was your weekend?")
    assert voice_model.langs == ["en-us"]


def test_only_a_listed_voice_can_be_chosen(client):
    assert client.put("/api/voice", json={"voice": "zz_nobody"}).status_code == 422
    assert [v["id"] for v in client.get("/api/voices").json() if v["chosen"]] == [speech.DEFAULT_VOICE]


def test_a_chosen_voice_comes_before_the_environment(client, monkeypatch):
    monkeypatch.setenv("TTS_VOICE", "am_puck")
    assert speech.current_voice() == "am_puck"
    client.put("/api/voice", json={"voice": "bm_george"})
    assert speech.current_voice() == "bm_george"
