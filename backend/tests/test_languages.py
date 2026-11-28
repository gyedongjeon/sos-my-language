"""The languages the app teaches: the learner chooses one on the first start, can go over to
another at any time, and what was learned in each is kept apart."""

import io
import json
import wave
from collections import Counter

import numpy as np
import pytest

from app import conversation, patterns, speech, topics, transcribe, videos
from app.db import SEED_TOPICS, choose_language, current_language, get_connection, init_db
from app.languages import LANGUAGES, LEVELS
from app.videos import Snippet, sentences
from tests.test_transcribe import FakeWhisperModel


def choose(client, code: str) -> list[dict]:
    response = client.put("/api/language", json={"language": code})
    assert response.status_code == 200, response.text
    return response.json()


# --- What a language needs --------------------------------------------------------------------


@pytest.mark.parametrize("language", LANGUAGES.values(), ids=lambda language: language.code)
def test_a_language_has_everything_the_app_teaches_with(language):
    assert language.name and language.native and language.locale.lower().startswith(language.code)
    assert language.subtitles[0] == language.code
    assert all(abbreviation == abbreviation.lower() for abbreviation in language.abbreviations)
    assert language.sample and language.pattern_slots and language.pattern_example and language.instruction_example
    # An opening line for every built-in topic, and no other.
    assert set(language.openers) == {title for title, *_ in SEED_TOPICS}
    assert all(opener.strip() for opener in language.openers.values())
    assert len({voice.id for voice in language.voices}) == len(language.voices) >= 1
    assert all(voice.label and voice.size > 0 and voice.engine in ("kokoro", "piper", "supertonic") for voice in language.voices)


@pytest.mark.parametrize("language", LANGUAGES.values(), ids=lambda language: language.code)
def test_a_language_has_patterns_at_every_level(language):
    for pattern in language.patterns:
        assert pattern.id and pattern.pattern and pattern.use and pattern.example
        assert not pattern.id.startswith(patterns.OWN_PREFIX)
    assert len({pattern.id for pattern in language.patterns}) == len(language.patterns)
    assert len({pattern.pattern for pattern in language.patterns}) == len(language.patterns)
    sizes = Counter(pattern.level for pattern in language.patterns)
    assert list(sizes) == LEVELS and all(size >= 5 for size in sizes.values()), sizes


def test_languages_are_told_apart_by_their_code():
    assert list(LANGUAGES) == [language.code for language in LANGUAGES.values()]
    assert len({language.name for language in LANGUAGES.values()}) == len(LANGUAGES)


# --- Choosing one -----------------------------------------------------------------------------


def test_no_language_is_chosen_on_the_first_start(client):
    choose_language(None)
    listed = client.get("/api/languages").json()
    assert [(language["code"], language["name"], language["native"]) for language in listed] == [
        ("en", "English", "English"),
        ("de", "German", "Deutsch"),
        ("ko", "Korean", "한국어"),
    ]
    assert not any(language["chosen"] for language in listed)
    assert all(language["locale"] and language["sample"] for language in listed)


def test_nothing_is_downloaded_before_a_language_is_chosen(client, monkeypatch):
    choose_language(None)
    started = []
    monkeypatch.setattr(speech, "_download_models", lambda: started.append("voice"))
    monkeypatch.setattr(transcribe, "_download", lambda: started.append("speech-to-text"))
    assert client.post("/api/models/download").status_code == 200
    assert all(model["state"] == "missing" for model in client.get("/api/models").json())
    assert started == []


def test_the_chosen_language_is_the_one_practised(client):
    assert [language["code"] for language in choose(client, "de") if language["chosen"]] == ["de"]
    assert current_language().name == "German"
    assert [language["code"] for language in client.get("/api/languages").json() if language["chosen"]] == ["de"]


def test_the_choice_is_kept_when_the_app_starts_again(client):
    choose(client, "de")
    init_db()
    assert current_language().code == "de"


def test_only_a_language_the_app_teaches_can_be_chosen(client):
    assert client.put("/api/language", json={"language": "tlh"}).status_code == 422
    assert current_language().code == "en"


# --- Each language has its own topics, conversations, videos, and patterns ---------------------


def test_the_built_in_topics_open_in_the_language_practised(client, german):
    listed = client.get("/api/topics").json()
    assert len(listed) == len(SEED_TOPICS)
    assert listed[0]["title"] == "Small talk" and listed[0]["opener"].startswith("Hallo!")


def test_an_own_topic_belongs_to_the_language_it_was_added_in(client):
    own = {"title": "Renting a car", "situation": "At the rental desk.", "opener": "Hello!"}
    assert client.post("/api/topics", json=own).status_code == 201
    choose(client, "de")
    assert "Renting a car" not in [topic["title"] for topic in client.get("/api/topics").json()]
    # The same title is free in another language.
    assert client.post("/api/topics", json={**own, "opener": "Guten Tag!"}).status_code == 201
    choose(client, "en")
    mine = [topic for topic in client.get("/api/topics").json() if topic["custom"]]
    assert [topic["opener"] for topic in mine] == ["Hello!"]


@pytest.fixture
def tutor(monkeypatch):
    """The model answers every turn with a correction, and records what it was told."""

    def complete(system, user, **params):
        complete.systems.append(system)
        return json.dumps({"reply": complete.reply, "correction": complete.correction})

    complete.systems, complete.reply = [], "I see!"
    complete.correction = {"original": "I go", "improved": "I went.", "explanation": "Past tense."}
    monkeypatch.setattr(conversation, "complete", complete)
    return complete


def talk(client, text: str) -> int:
    """A conversation on the first topic of the language practised, with one line and its reply."""
    topic = client.get("/api/topics").json()[0]["id"]
    started = client.post("/api/conversations", json={"topic_id": topic}).json()
    client.post(f"/api/conversations/{started['id']}/messages", json={"text": text})
    assert client.post(f"/api/conversations/{started['id']}/reply").status_code == 200
    return started["id"]


def test_the_history_lists_the_conversations_of_the_language_practised(client, tutor):
    english = talk(client, "I go to the beach.")
    choose(client, "de")
    tutor.reply = "Ach so!"
    tutor.correction = {"original": "Ich gehe", "improved": "Ich bin gegangen.", "explanation": "Perfekt."}
    german = talk(client, "Ich gehe gestern an den Strand.")
    assert [(c["id"], c["language"]) for c in client.get("/api/conversations").json()] == [(german, "de")]
    choose(client, "en")
    assert [(c["id"], c["language"]) for c in client.get("/api/conversations").json()] == [(english, "en")]
    # One opened by its link says which language it is in, so the page can go over to it.
    assert client.get(f"/api/conversations/{german}").json()["language"] == "de"
    assert client.get(f"/api/conversations/{german}").json()["messages"][0]["text"].startswith("Hallo!")


def test_the_corrections_listed_are_those_of_the_language_practised(client, tutor):
    talk(client, "I go to the beach.")
    choose(client, "de")
    tutor.correction = {"original": "Ich gehe", "improved": "Ich bin gegangen.", "explanation": "Perfekt."}
    talk(client, "Ich gehe gestern an den Strand.")
    assert [c["improved"] for c in client.get("/api/corrections").json()] == ["Ich bin gegangen."]
    choose(client, "en")
    assert [c["improved"] for c in client.get("/api/corrections").json()] == ["I went."]


def test_the_partner_is_told_which_language_to_speak(client, tutor):
    talk(client, "I go to the beach.")
    assert "friendly English conversation partner" in tutor.systems[-1]
    assert "German" not in tutor.systems[-1] and '"du"' not in tutor.systems[-1]
    choose(client, "de")
    talk(client, "Ich gehe gestern an den Strand.")
    assert "friendly German conversation partner" in tutor.systems[-1]
    assert 'Use "du" or "Sie" as the situation calls for' in tutor.systems[-1]
    # Nothing of the prompt is left to be filled in.
    assert "{" not in tutor.systems[-1].split("Reply with a single JSON object")[0]


def test_the_explanation_is_asked_for_in_the_learners_language_not_the_one_practised(client, tutor, german):
    client.put("/api/settings", json={"feedback_language": "Korean"})
    talk(client, "Ich gehe gestern an den Strand.")
    assert "Do not use German for it, apart from German words and examples quoted in Korean." in tutor.systems[-1]
    client.put("/api/settings", json={"feedback_language": "German"})
    talk(client, "Ich gehe gestern an den Strand.")
    assert "Do not use German for it" not in tutor.systems[-1]


def test_the_first_line_of_an_own_topic_is_written_in_the_language_practised(client, german, monkeypatch):
    asked = []

    def complete(system, user, **params):
        asked.append(system)
        return json.dumps({"opener": "Guten Tag! Was kann ich für Sie tun?"})

    monkeypatch.setattr(topics, "complete", complete)
    made = client.post("/api/topics", json={"title": "Renting a car", "situation": "At the rental desk."}).json()
    assert made["opener"] == "Guten Tag! Was kann ich für Sie tun?"
    assert "natural, everyday German" in asked[0] and 'Use "du" or "Sie"' in asked[0]


SPEECH = [Snippet(0.0, 4.0, "Guten Morgen. Ich erzähle Ihnen heute von den Ärzten in Österreich.")]


@pytest.fixture
def youtube(monkeypatch):
    """YouTube has subtitles for one video, in whichever language is asked for."""

    def transcript(video_id):
        transcript.asked.append(current_language().code)
        return SPEECH, current_language().code, False

    transcript.asked = []
    monkeypatch.setattr(videos, "_transcript", transcript)
    monkeypatch.setattr(videos, "_about", lambda video_id: ("A talk", "A channel"))
    monkeypatch.setattr(videos, "_estimate", lambda lines: "B1")
    return transcript


URL = "https://www.youtube.com/watch?v=UF8uR6Z6KLc"


def test_a_video_belongs_to_the_language_it_was_saved_for(client, youtube, german):
    saved = client.post("/api/videos", json={"url": URL}).json()
    assert [video["id"] for video in client.get("/api/videos").json()] == [saved["id"]]
    choose(client, "en")
    assert client.get("/api/videos").json() == []
    assert client.get(f"/api/videos/{saved['id']}").status_code == 404
    assert client.get("/api/video-lines", params={"q": "Morgen"}).json() == []
    # The same video can be saved again for another language, with that language's subtitles.
    again = client.post("/api/videos", json={"url": URL})
    assert again.status_code == 201 and again.json()["id"] != saved["id"]
    assert youtube.asked == ["de", "en"]


# The real function, kept before conftest's fixture replaces it for each test.
videos_transcript = videos._transcript


def test_a_video_without_subtitles_in_the_language_practised_says_so(german):
    class NoTracks:
        def list(self, video_id):
            raise videos.NoTranscriptFound(video_id, ["de"], [])

    videos.YouTubeTranscriptApi, kept = NoTracks, videos.YouTubeTranscriptApi
    try:
        with pytest.raises(videos.NoSubtitles, match="no German subtitles"):
            # conftest replaces `_transcript` for every test; this is the function itself.
            videos_transcript("UF8uR6Z6KLc")
    finally:
        videos.YouTubeTranscriptApi = kept


def test_the_search_of_saved_sentences_ignores_the_case_of_umlauts(client, youtube, german):
    client.post("/api/videos", json={"url": URL})
    assert len(client.get("/api/video-lines", params={"q": "ÄRZTEN"}).json()) == 1
    assert len(client.get("/api/video-lines", params={"q": "österreich"}).json()) == 1


def test_each_language_has_its_own_patterns_and_progress(client):
    english = client.get("/api/patterns").json()
    assert english[0]["id"] == LANGUAGES["en"].patterns[0].id
    client.post(f"/api/patterns/{english[0]['id']}/results", json={"correct": 4, "total": 5})
    choose(client, "de")
    german = client.get("/api/patterns").json()
    assert [pattern["id"] for pattern in german] == [pattern.id for pattern in LANGUAGES["de"].patterns]
    assert all(pattern["sessions"] == 0 for pattern in german)
    # A pattern of another language is not one of this language.
    assert client.post(f"/api/patterns/{english[0]['id']}/results", json={"correct": 1, "total": 5}).status_code == 404
    client.post(f"/api/patterns/{german[0]['id']}/results", json={"correct": 5, "total": 5})
    choose(client, "en")
    assert client.get("/api/patterns").json()[0]["last_correct"] == 4


def test_pattern_sentences_are_asked_for_in_the_language_practised(client, german, monkeypatch):
    asked = []

    def complete(system, user, **params):
        asked.append(system)
        return json.dumps({"note": "Höflich bitten.", "items": [{"prompt": "커피 한 잔 주세요.", "answer": "Ich möchte einen Kaffee."}]})

    monkeypatch.setattr(patterns, "complete", complete)
    client.put("/api/settings", json={"feedback_language": "Korean"})
    pattern = LANGUAGES["de"].patterns[0]
    assert client.post(f"/api/patterns/{pattern.id}/exercises").status_code == 200
    assert "You are a teacher of German" in asked[0] and "says it in German" in asked[0]
    assert "Because that language is German" not in asked[0]
    # With German as the learner's own language too, the sentence is shown as an instruction.
    client.put("/api/settings", json={"feedback_language": "German"})
    client.post(f"/api/patterns/{pattern.id}/exercises")
    assert "Because that language is German" in asked[1] and "Sag, dass du bereust" in asked[1]


# --- Words as heard, and subtitles, in German ---------------------------------------------------


def practise(client, tutor, improved: str, said: str) -> dict:
    tutor.correction = {"original": "…", "improved": improved, "explanation": "…"}
    talk(client, "Etwas, was ich gesagt habe.")
    correction = client.get("/api/corrections").json()[0]["id"]
    return client.post(f"/api/corrections/{correction}/attempts", json={"text": said}).json()


def test_german_short_forms_and_sharp_s_are_heard_the_same(client, tutor, german):
    assert practise(client, tutor, "Wie geht's?", "Wie geht es?")["matched"] is True
    # Speech recognition may write either, as Swiss German does.
    assert practise(client, tutor, "Ich heiße Alex.", "Ich heisse Alex.")["matched"] is True
    assert practise(client, tutor, "Ich habe drei Katzen.", "Ich habe 3 Katzen")["matched"] is True
    assert practise(client, tutor, "Ich habe drei Katzen.", "Ich habe zwei Katzen")["matched"] is False


def test_english_short_forms_are_not_spelled_out_in_german(client, tutor, german):
    assert practise(client, tutor, "I am here.", "I'm here.")["matched"] is False


def test_a_german_abbreviation_does_not_end_a_sentence(german):
    said = [Snippet(0.0, 6.0, "Wir essen z.B. Brot und Käse. Dr. Weber kommt um ca. acht. Danke.")]
    assert [line.text for line in sentences(said)] == ["Wir essen z.B. Brot und Käse.", "Dr. Weber kommt um ca. acht.", "Danke."]


def test_stage_directions_are_left_out_in_any_language():
    talk = [Snippet(0.0, 4.0, "Und dann (Gelächter) ging es los."), Snippet(4.0, 2.0, "(Beifall) Vielen Dank.")]
    assert [line.text for line in sentences(talk)] == ["Und dann ging es los.", "Vielen Dank."]
    said = [Snippet(0.0, 4.0, "It works (most of the time) for us. (Laughter) Thank you.")]
    assert [line.text for line in sentences(said)] == ["It works (most of the time) for us.", "Thank you."]


# --- Hearing and speaking ---------------------------------------------------------------------


@pytest.fixture
def whisper(monkeypatch):
    FakeWhisperModel.loads = []
    asked = []

    def hear(self, audio, **options):
        asked.append(options["language"])
        return [], None

    monkeypatch.setattr(FakeWhisperModel, "transcribe", hear, raising=False)
    monkeypatch.setattr(transcribe, "WhisperModel", FakeWhisperModel)
    monkeypatch.setattr(transcribe, "_model", None)
    monkeypatch.setattr(transcribe, "_loaded", None)
    monkeypatch.setattr(transcribe, "_is_downloaded", lambda: True)
    monkeypatch.delenv("WHISPER_MODEL", raising=False)
    return asked


def test_speech_is_recognized_in_the_language_practised(whisper):
    transcribe.transcribe(io.BytesIO(b"audio"))
    choose_language("de")
    transcribe.transcribe(io.BytesIO(b"audio"))
    assert whisper == ["en", "de"]
    # English has a model of its own; German is heard by the multilingual one.
    assert [load["name"] for load in FakeWhisperModel.loads] == ["small.en", "small"]


def test_an_english_only_model_from_the_environment_is_not_used_for_german(whisper, monkeypatch, german):
    monkeypatch.setenv("WHISPER_MODEL", "medium.en")
    transcribe._get_model()
    monkeypatch.setenv("WHISPER_MODEL", "medium")
    transcribe._get_model()
    assert [load["name"] for load in FakeWhisperModel.loads] == ["small", "medium"]


class FakePiperVoice:
    """Stands in for a Piper voice: half a second of silence per request."""

    calls: list[str] = []

    def __init__(self, model_path):
        self.name = model_path.name.removesuffix(".onnx")

    @classmethod
    def load(cls, model_path, config_path=None):
        return cls(model_path)

    def synthesize_wav(self, text, wav_file):
        FakePiperVoice.calls.append(f"{self.name}: {text}")
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(22050)
        wav_file.writeframes(b"\0\0" * 11025)


def put_voice(voice: str) -> None:
    for name in speech.model_files(voice):
        (speech.TTS_DIR / name).parent.mkdir(parents=True, exist_ok=True)
        (speech.TTS_DIR / name).write_bytes(b"model")


@pytest.fixture
def piper(monkeypatch):
    FakePiperVoice.calls = []
    monkeypatch.setattr(speech, "PiperVoice", FakePiperVoice)
    monkeypatch.setattr(speech, "_download_models", lambda: None)
    return FakePiperVoice


def test_german_lines_are_read_by_a_german_voice(client, piper, german):
    put_voice("de_DE-thorsten-high")
    response = client.post("/api/speech", json={"text": "Wie war dein Wochenende?"})
    assert response.status_code == 200 and response.content.startswith(b"RIFF")
    assert piper.calls == ["de_DE-thorsten-high: Wie war dein Wochenende?"]


def test_each_language_lists_its_own_voices_and_says_which_are_downloaded(client, german):
    put_voice("de_DE-kerstin-low")
    listed = client.get("/api/voices").json()
    assert [voice["id"] for voice in listed] == [voice.id for voice in LANGUAGES["de"].voices]
    assert [voice["id"] for voice in listed if voice["chosen"]] == ["de_DE-thorsten-high"]
    assert [voice["id"] for voice in listed if voice["downloaded"]] == ["de_DE-kerstin-low"]
    assert all(voice["size"] > 0 for voice in listed)


def test_a_voice_is_chosen_for_one_language_only(client, piper):
    client.put("/api/voice", json={"voice": "bm_george"})
    choose(client, "de")
    assert speech.current_voice() == "de_DE-thorsten-high"
    # A voice of another language cannot be chosen.
    assert client.put("/api/voice", json={"voice": "bm_george"}).status_code == 422
    client.put("/api/voice", json={"voice": "de_DE-ramona-low"})
    assert speech.current_voice() == "de_DE-ramona-low"
    choose(client, "en")
    assert speech.current_voice() == "bm_george"


def test_choosing_a_voice_starts_its_download_with_its_size(client, german, monkeypatch):
    fetched = []
    monkeypatch.setattr(speech, "_download_models", lambda: fetched.append(speech.current_voice()))
    client.put("/api/voice", json={"voice": "de_DE-ramona-low"})
    # The fake download writes nothing, so only its end is waited for.
    speech.model_download._thread.join(5)
    assert fetched == ["de_DE-ramona-low"]
    voice = next(model for model in client.get("/api/models").json() if model["id"] == "voice")
    assert voice["total"] == speech.voices()["de_DE-ramona-low"].size


def test_a_piper_voice_is_downloaded_from_its_folder_of_the_collection(german, monkeypatch):
    requested = []

    def urlopen(url, context=None):
        requested.append(url)
        return io.BytesIO(b"model-bytes")

    monkeypatch.setattr(speech.urllib.request, "urlopen", urlopen)
    speech._download_models()
    folder = f"{speech.PIPER_URL}/de/de_DE/thorsten/high"
    assert requested == [f"{folder}/de_DE-thorsten-high.onnx", f"{folder}/de_DE-thorsten-high.onnx.json"]
    assert sorted(path.name for path in speech.TTS_DIR.iterdir()) == ["de_DE-thorsten-high.onnx", "de_DE-thorsten-high.onnx.json"]


def test_the_voice_of_one_language_is_there_while_that_of_another_is_missing(client, german):
    for name in speech.KOKORO_FILES:
        speech.TTS_DIR.mkdir(parents=True, exist_ok=True)
        (speech.TTS_DIR / name).write_bytes(b"model")
    voice = next(model for model in client.get("/api/models").json() if model["id"] == "voice")
    assert voice["state"] == "missing"
    choose(client, "en")
    voice = next(model for model in client.get("/api/models").json() if model["id"] == "voice")
    assert voice["state"] == "ready"


# --- Korean ---------------------------------------------------------------------------------


def test_the_korean_partner_is_told_which_speech_level_to_use(client, tutor, korean):
    talk(client, "어제 바다에 가요.")
    assert "friendly Korean conversation partner" in tutor.systems[-1]
    assert "해요체" in tutor.systems[-1] and "반말" in tutor.systems[-1]


def test_the_built_in_topics_open_in_korean(client, korean):
    assert client.get("/api/topics").json()[0]["opener"].startswith("안녕하세요")


def test_korean_numbers_are_heard_as_figures(client, tutor, korean):
    assert practise(client, tutor, "고양이가 셋 있어요.", "고양이가 3 있어요")["matched"] is True
    assert practise(client, tutor, "고양이가 셋 있어요.", "고양이가 둘 있어요")["matched"] is False


class FakeSupertonic:
    """Stands in for Supertonic: a quarter of a second of silence per request, as a row of samples."""

    calls: list[str] = []
    sample_rate = 44100

    def __init__(self, model, model_dir, auto_download):
        assert (model, auto_download) == ("supertonic-3", False)
        assert (model_dir / "onnx" / "tts.json").exists()

    def get_voice_style(self, voice_name):
        return voice_name

    def synthesize(self, text, voice_style, lang):
        FakeSupertonic.calls.append(f"{voice_style} ({lang}): {text}")
        return np.zeros((1, 11025), dtype=np.float32), np.array([0.25])


@pytest.fixture
def supertonic(monkeypatch):
    FakeSupertonic.calls = []
    monkeypatch.setattr(speech, "Supertonic", FakeSupertonic)
    monkeypatch.setattr(speech, "_download_models", lambda: None)
    return FakeSupertonic


def test_korean_lines_are_read_by_a_supertonic_voice(client, supertonic, korean):
    put_voice("F1")
    response = client.post("/api/speech", json={"text": "주말 잘 보냈어요?"})
    assert response.status_code == 200
    with wave.open(io.BytesIO(response.content)) as clip:
        assert (clip.getframerate(), clip.getnframes()) == (44100, 11025)
    assert supertonic.calls == ["F1 (ko): 주말 잘 보냈어요?"]


def test_supertonic_voices_share_one_model_and_each_has_its_own_style(korean):
    put_voice("F1")
    assert speech.is_downloaded("F1") and not speech.is_downloaded("M2")
    assert speech.model_files("M2")[:-1] == speech.model_files("F1")[:-1]


def test_a_supertonic_voice_is_downloaded_from_the_archive_of_the_model(korean, monkeypatch):
    requested = []

    def urlopen(url, context=None):
        requested.append(url)
        return io.BytesIO(b"model-bytes")

    monkeypatch.setattr(speech.urllib.request, "urlopen", urlopen)
    speech._download_models()
    assert requested == [f"{speech.SUPERTONIC_URL}/{name}" for name in (*speech.SUPERTONIC_FILES, "voice_styles/F1.json")]
    assert speech.is_downloaded("F1")
    assert not list(speech.TTS_DIR.rglob("*.part"))


def test_every_row_that_is_learned_says_which_language_it_is_in():
    with get_connection() as conn:
        tables = [row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]
        with_target = {
            table for table in tables if "target" in [column["name"] for column in conn.execute(f"PRAGMA table_info({table})")]
        }
    assert with_target == {
        "topics",
        "conversations",
        "pattern_progress",
        "videos",
        "own_patterns",
        "pattern_mistakes",
        "shadowing_mistakes",
        "shadowing_attempts",
        "word_lookups",
        "saved_words",
    }
